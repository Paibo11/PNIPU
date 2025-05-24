import string
import random
ALPHABET = string.ascii_uppercase

def readfile(file):
    f=open(file, mode='r')
    message=''
    for ch in f.read():
        if 65 <= ord(ch) <= 90 or 97 <= ord(ch) <= 122:
            message+=ch.upper()
    f.close()
    return message

#Build shifted alphabet
def offset(char, offset):
    return ALPHABET[(ALPHABET.index(char)+offset)%26]

class Playfair:
    @staticmethod
    def buildtable(key):
        return ''.join(sorted(set(key), key=lambda x: key.index(x)))+''.join([ch for ch in ALPHABET if not (ch in key) and ch!='J'])


    @staticmethod
    def padding(message):
        list_message=list(message)
        i = 1
        while i < len(list_message):
            if list_message[i]==list_message[i-1]:
                list_message.insert(i, 'X')
            i += 2
        if len(list_message)%2!=0:
            list_message.append('X')
        return [''.join(list_message[a:a+2]) for a in range(0, len(list_message), 2)]

    @staticmethod
    def substitution(message, table, *, mode):

        #table=Playfair.buildtable(key)
        if mode == 1:
            message=message.replace('J', 'I')
        list_message=Playfair.padding(message)
        list_pos=[[[table.index(elem[0])//5, table.index(elem[0])%5], [table.index(elem[1])//5, table.index(elem[1])%5]] for elem in list_message]
        list_pos2=[]
        for elem in list_pos:
            if elem[0][0]==elem[1][0]:
                list_pos2.append([[elem[0][0], (elem[0][1]+mode)%5], [elem[1][0], (elem[1][1]+mode)%5]])
            elif elem[0][1]==elem[1][1]:
                list_pos2.append([[(elem[0][0]+mode)%5, elem[0][1]], [(elem[1][0]+mode)%5, elem[1][1]]])
            else:
                list_pos2.append([[elem[0][0], elem[1][1]], [elem[1][0], elem[0][1]]])
        c=''.join([table[e[0][0]*5+e[0][1]]+table[e[1][0]*5+e[1][1]] for e in list_pos2])
        return c

    @staticmethod
    def encrypt(message, key):
        return Playfair.substitution(message, key, mode=1)

    @staticmethod
    def decrypt(message, key):
        return Playfair.substitution(message, key, mode=-1)


if __name__=='__main__':

    #Playfair test
    print('---Playfair Cipher---')
    key=Playfair.buildtable('charity'.upper())
    c = Playfair.encrypt('ILIVEINAHOUSENEARTHEMOUNTAINSIHAVETWOBROTHERSANDONESISTERANDIWASBORNLASTMYFATHERTEACHESMATHEMATICSANDMYMOTHERISANURSEATABIGHOSPITALMYBROTHERSAREVERYSMARTANDWORKHARDINSCHOOLMYSISTERISANERVOUSGIRLBUTSHEISVERYKINDMYGRANDMOTHERALSOLIVESWITHUSSHECAMEFROMITALYWHENIWASTWOYEARSOLDSHEHASGROWNOLDBUTSHEISXSTILLVERYSTRONGSHECOOKSTHEBESTFOODMYFAMILYISVERYIMPORTANTXTOMEWEDOLOTSOFTHINGSTOGETHERMYBROTHERSANDILIKETOGOONLONGWALKSINTHEMOUNTAINSMYSISTERLIKESTOCOOKWITHMYGRANDMOTHERONTHEWEEKENDSWEALLPLAYBOARDGAMESTOGETHERWELAUGHANDALWAYSHAVEAGOODTIMEILOVEMYFAMILYVERYMUCHX'.upper(), key)
    print(c)
    d = Playfair.decrypt(c, key)
    print(d)


