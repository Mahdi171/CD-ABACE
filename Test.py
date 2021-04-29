from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from charm.toolbox.secretutil import SecretUtil
from charm.toolbox.ABEnc import ABEnc, Input, Output
from collections import defaultdict
from Zeropoly import Zero_poly
from Main import CPabe_SP21
# type annotations'
groupObj = PairingGroup('/home/mahdi/Desktop/pbc-0.5.14/param/f.param', param_file=True)
cpabe = CPabe_SP21(groupObj)


# RA setup
U = ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN']
(pk, mk) = cpabe.RAgen(10, U)

# SA setup
(sgk,vk) = cpabe.SAgen(pk)

# Encryption key generation
P = ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE']
(ek,sign) = cpabe.EncKGen(pk, sgk, vk, P, U)
print("Signature :=>", sign)

# Decryption key generation
B = ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX']
dk = cpabe.DecKGen(pk, mk, B, U)
print("dk :=>", dk)

# Encryption
rand_msg = groupObj.random(GT)
(ct, Rand) = cpabe.encrypt(pk, vk, rand_msg, ek, sign, P)
print("\nCiphertext...\n", ct)


# Sanitization
(ctt) = cpabe.Sanitization(pk, vk, ct, Rand)
print("\n Sanitized Ciphertext...\n", ctt)

# Decryption
rec_msg = cpabe.decrypt(pk, dk, ctt)
print("\nDecrypt...\n")
print("Rec msg =>", rec_msg)
print("\nRand msg =>", rand_msg)

if rand_msg==rec_msg:
    print("\nIt is correct")
else:
    print("\nIt is wrong")
