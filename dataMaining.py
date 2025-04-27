import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import train_test_split
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings

warnings.filterwarnings('ignore')
plt.style.use('ggplot')


class TimeSeriesPredictor:
    def __init__(self, file_path, date_col, target_col, feature_cols=None, look_back=3):
        self.file_path = file_path
        self.date_col = date_col
        self.target_col = target_col
        self.feature_cols = feature_cols if feature_cols else []
        self.look_back = look_back
        self.scaler_features = MinMaxScaler()
        self.scaler_target = MinMaxScaler()
        self.model = None
        self.data = None

    def load_data(self):
        """Загрузка и предобработка данных"""
        try:
            self.data = pd.read_csv(self.file_path, parse_dates=[self.date_col])
            self.data.set_index(self.date_col, inplace=True)

            # Проверка данных
            print("Первые 5 строк данных:")
            print(self.data.head())
            print("\nСтатистика данных:")
            print(self.data.describe())

        except Exception as e:
            print(f"Ошибка при загрузке данных: {e}")
            raise

    def prepare_data(self, test_size=0.2):
        """Подготовка данных для обучения"""
        # Раздельная нормализация признаков и целевой переменной
        if self.feature_cols:
            self.data[self.feature_cols] = self.scaler_features.fit_transform(self.data[self.feature_cols])

        self.data[[self.target_col]] = self.scaler_target.fit_transform(self.data[[self.target_col]])

        # Создание временных окон
        X, y = [], []
        for i in range(len(self.data) - self.look_back):
            # Базовые признаки временного ряда
            time_series_features = self.data[self.target_col].values[i:(i + self.look_back)]

            # Дополнительные признаки (если есть)
            extra_features = []
            for feature in self.feature_cols:
                extra_features.append(self.data[feature].values[i + self.look_back - 1])

            # Объединяем все признаки
            all_features = np.concatenate([time_series_features, extra_features])
            X.append(all_features)
            y.append(self.data[self.target_col].values[i + self.look_back])

        X, y = np.array(X), np.array(y)

        # Разделение на train/test
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=test_size, shuffle=False
        )

    def build_model(self, hidden_layers=(50, 50), max_iter=2000, learning_rate=0.001):
        """Построение и обучение модели"""
        self.model = MLPRegressor(
            hidden_layer_sizes=hidden_layers,
            activation='relu',
            solver='adam',
            max_iter=max_iter,
            random_state=42,
            early_stopping=True,
            learning_rate_init=learning_rate,
            batch_size=16,
            alpha=0.001  # Регуляризация
        )

        print("\nОбучение модели...")
        self.model.fit(self.X_train, self.y_train)
        print("Обучение завершено.")

        # Оценка модели
        train_score = self.model.score(self.X_train, self.y_train)
        test_score = self.model.score(self.X_test, self.y_test)
        print(f"\nR2 score на тренировочных данных: {train_score:.4f}")
        print(f"R2 score на тестовых данных: {test_score:.4f}")

    def evaluate(self):
        """Оценка качества модели"""
        y_pred = self.model.predict(self.X_test)

        # Обратное преобразование масштаба
        y_test_inv = self.scaler_target.inverse_transform(self.y_test.reshape(-1, 1)).flatten()
        y_pred_inv = self.scaler_target.inverse_transform(y_pred.reshape(-1, 1)).flatten()

        # Метрики качества
        mae = mean_absolute_error(y_test_inv, y_pred_inv)
        mse = mean_squared_error(y_test_inv, y_pred_inv)
        rmse = np.sqrt(mse)

        print("\nОценка качества модели:")
        print(f"MAE: {mae:.2f}")
        print(f"MSE: {mse:.2f}")
        print(f"RMSE: {rmse:.2f}")

        return y_test_inv, y_pred_inv

    def predict_future(self, steps=6, future_features=None):
        """
        Прогнозирование на будущие периоды
        """
        # Подготовка последних известных значений
        last_known = self.data.iloc[-self.look_back:].copy()

        predictions = []
        dates = []

        for i in range(steps):
            # Подготовка входных данных
            time_series_part = last_known[self.target_col].values[-self.look_back:]

            # Обработка дополнительных признаков
            extra_part = []
            if self.feature_cols:
                if future_features is not None and i < len(future_features):
                    # Нормализуем будущие признаки
                    scaled_features = self.scaler_features.transform(
                        future_features.iloc[i][self.feature_cols].values.reshape(1, -1)
                    )
                    extra_part = scaled_features.flatten()
                else:
                    # Если будущие значения не предоставлены, используем последние известные
                    extra_part = last_known[self.feature_cols].iloc[-1].values

            # Формируем входной вектор
            input_data = np.concatenate([time_series_part, extra_part]).reshape(1, -1)

            # Делаем прогноз
            pred = self.model.predict(input_data)[0]
            predictions.append(pred)

            # Создаем новую дату
            last_date = last_known.index[-1]
            new_date = last_date + pd.DateOffset(months=1)

            # Обновляем last_known для следующего шага
            new_row = {self.target_col: pred}
            for j, col in enumerate(self.feature_cols):
                new_row[col] = extra_part[j] if self.feature_cols else 0

            new_row_df = pd.DataFrame([new_row], index=[new_date])
            last_known = pd.concat([last_known, new_row_df])[-self.look_back:]

            dates.append(new_date)

        # Обратное преобразование прогнозов
        predictions = self.scaler_target.inverse_transform(
            np.array(predictions).reshape(-1, 1)
        ).flatten()

        return dates, predictions

    def plot_results(self, y_test_inv, y_pred_inv, future_dates=None, future_pred=None):
        """Визуализация результатов"""
        try:
            plt.figure(figsize=(14, 7))

            # Исторические данные
            plt.plot(
                self.data.index,
                self.scaler_target.inverse_transform(self.data[[self.target_col]]),
                label='Исторические данные'
            )

            # Прогноз на тестовый период
            test_dates = self.data.index[-len(y_test_inv):]
            plt.plot(
                test_dates,
                y_pred_inv,
                'g-',
                linewidth=2,
                label='Прогноз на тестовый период'
            )

            # Прогноз на будущее (если есть)
            if future_dates is not None and future_pred is not None:
                plt.plot(
                    future_dates,
                    future_pred,
                    'r--',
                    linewidth=2,
                    label='Прогноз на будущее'
                )

            plt.legend()
            plt.title(f'Прогноз {self.target_col}')
            plt.xlabel('Дата')
            plt.ylabel('Значение')
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.tight_layout()

            # Сохранение графика
            plot_file = f"{self.target_col}_forecast.png"
            plt.savefig(plot_file, dpi=300)
            print(f"\nГрафик сохранен как '{plot_file}'")
            plt.close()

        except Exception as e:
            print(f"\nОшибка при построении графика: {e}")


if __name__ == "__main__":
    try:
        # Конфигурация
        config = {
            'file_path': 'sales_data.csv',
            'date_col': 'date',
            'target_col': 'sales',
            'feature_cols': ['advertising', 'competitors'],
            'look_back': 4
        }

        # Инициализация и запуск
        predictor = TimeSeriesPredictor(**config)
        predictor.load_data()
        predictor.prepare_data(test_size=0.2)

        # Настройка модели
        predictor.build_model(
            hidden_layers=(30, 30),  # Упростим архитектуру
            max_iter=5000,
            learning_rate=0.0001  # Уменьшим learning rate
        )

        # Оценка модели
        y_test, y_pred = predictor.evaluate()

        # Прогноз на будущее (6 месяцев)
        future_features = pd.DataFrame({
            'advertising': [8500, 9000, 9500, 10000, 10500, 11000],
            'competitors': [6, 6, 5, 5, 4, 4]
        })

        future_dates, future_pred = predictor.predict_future(
            steps=6,
            future_features=future_features
        )

        # Визуализация
        predictor.plot_results(y_test, y_pred, future_dates, future_pred)

        # Вывод прогноза
        print("\nПрогноз на будущие периоды:")
        for date, pred in zip(future_dates, future_pred):
            print(f"{date.strftime('%Y-%m')}: {pred:.2f}")

    except Exception as e:
        print(f"\nПроизошла ошибка: {e}")