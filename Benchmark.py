from charm.toolbox.pairinggroup import PairingGroup,ZR,G1,G2,GT,pair
from charm.toolbox.secretutil import SecretUtil
from charm.toolbox.ABEnc import ABEnc, Input, Output
from Zeropoly import Zero_poly
from openpyxl import load_workbook
from openpyxl import Workbook
from PoK import PoK
from charm.core.engine.util import serializeDict,objectToBytes

pk_t = { 'g_2':G1, 'h_i':G2, 'e_gg_alpha':GT, 'uni': str}
mk_t = {'alpha':ZR, 'g':G1 }
sk_t = { 'dk':G1, 'B':str }
ct_t = { 'C':GT, 'C1':G1, 'C2':G2, 'policy':str }
vk_t = { 'vk':G1 , 'Y': G2}
ek_t = { 'ek':G2 }
sgk_t = {'v':ZR }
sign_t = { 'R':G1, 'S':G2, 'T':G2, 'W':G2 }
Rand_t = { 'Rprime':G1, 'Sprime':G2, 'Tprime':G2, 'Wprime':G2, 'vkprime': G1, 'ekprime':G2}
ctt_t = { 'Cprime':GT, 'C1prime':G1, 'C2prime':G2, 'policy': str }

class CPabe_SP21(ABEnc):
    def __init__(self, groupObj):
        ABEnc.__init__(self)
        global util, group
        util = SecretUtil(groupObj, verbose=False)
        group = groupObj
    
    @Output(pk_t, mk_t)    
    def RAgen(self,uni_size,U):
        g, h, alpha = group.random(G1), group.random(G2), group.random(ZR)
        g.initPP(); h.initPP()
        g_2 = g ** (alpha**2)
        e_gg_alpha = pair(g,h)**alpha
        h_i= {}
        for j in range(uni_size+1):
            h_i[j] = h ** (alpha ** j)
        pk = {'g_2':g_2, 'h_i':h_i, 'e_gg_alpha':e_gg_alpha, 'uni': U}
        mk = {'alpha':alpha, 'g':g }
        return (pk, mk)

    @Input(pk_t)
    @Output(sgk_t, vk_t)
    def SAgen(self, pk):
        v = group.random(ZR); Y = group.random(G2)
        V = pk['g_2'] ** v
        sgk = {'v':v}
        vk = {'vk':V, 'Y':Y}
        return (sgk, vk)

    @Input(pk_t, mk_t, list, list)
    @Output(sk_t)
    def DecKGen(self, pk, mk, B, U):
        S= list(set(U) - set(B)); Zerop=1
        for attrs in S:
            Zerop *= mk['alpha'] + group.hash(attrs, ZR) 
        dk = mk['g'] ** (1/Zerop)
        return { 'dk':dk, 'B':B }

    @Input(pk_t, sgk_t, vk_t, list, list)
    @Output(ek_t, sign_t)
    def EncKGen(self, pk, sgk, vk, P, U):
        a=[]; Ek=1
        Com_set= list(set(pk['uni']) - set(P))
        for attrs in Com_set:
            a.append(group.hash(attrs, ZR))
        (indices,coeff_mult)=Zero_poly(a,len(a)-1,[0],[1])
        Coeffs=list(reversed(coeff_mult))
        for i in range(len(indices)):
            Ek*= (pk['h_i'][i+1] ** Coeffs[i])
        ek = {'ek':Ek}
        t = group.random(ZR)
        R = pk['g_2']**t
        S = (Ek ** (sgk['v']/t)) * (vk['Y']**(1/t))
        T = (S ** (sgk['v']/t)) * (pk['h_i'][0]**(1/t))
        W = pk['h_i'][0]**(1/t)
        sign={'R':R, 'S':S, 'T':T, 'W':W}
        return (ek,sign)

    @Input(pk_t, vk_t, GT, ek_t, sign_t, list)
    @Output(ct_t, Rand_t)
    def encrypt(self, pk, vk, M, ek, sign, P): 
        r = group.random(ZR)     
        C = M * (pk['e_gg_alpha'] ** r)
        C1 = pk['g_2'] ** (-r)
        C2 = ek['ek'] ** r
        ct = { 'C':C ,'C1':C1, 'C2':C2, 'policy':P}
        tprime = group.random(ZR)
        Rprime = sign['R'] ** (1/tprime)
        Sprime = sign['S'] ** tprime
        Tprime = (sign['T'] ** (tprime**2))* (sign['W']**(tprime*(1-tprime)))
        Wprime = sign['W'] ** (1/tprime)
        vkprime = vk['vk'] ** (1/tprime)
        ekprime = ek['ek'] ** tprime
        Rand = { 'Rprime':Rprime, 'Sprime':Sprime, 'Tprime':Tprime, 'Wprime':Wprime, 'vkprime': vkprime, 'ekprime':ekprime}
        return (ct,Rand)
    
    @Input(pk_t, vk_t, ct_t, Rand_t)
    @Output(ctt_t)
    def Sanitization(self, pk, vk, ct, Rand):
        a = []; C2prime = 1; s = group.random(ZR)
        if pair(Rand['Rprime'],Rand['Sprime'])==pair(Rand['vkprime'],Rand['ekprime'])*pair(pk['g_2'],vk['Y']) and pair(Rand['Rprime'],Rand['Tprime'])==pair(vk['vk'],Rand['Sprime'])*pair(pk['g_2'],pk['h_i'][0]):
            Com_set = list(set(pk['uni']) - set(ct['policy']))
            for attrs in Com_set:
                a.append(group.hash(attrs, ZR))
            (indices,coeff_mult) = Zero_poly(a,len(a)-1,[0],[1])
            Coeffs = list(reversed(coeff_mult))
            for i in range(len(indices)):
                C2prime *= (pk['h_i'][i+1] ** Coeffs[i])
            Cprime = ct['C'] * (pk['e_gg_alpha']**s)
            C1prime = ct['C1'] * (pk['g_2']**(-s))
            C2prime = ct['C2'] * (C2prime**s)
            ctt = { 'Cprime':Cprime, 'C1prime':C1prime, 'C2prime':C2prime, 'policy':ct['policy'] }
            return (ctt)
        else:
            return (None)

    @Input(pk_t, sk_t, ctt_t)
    @Output(GT)
    def decrypt(self, pk, sk, ctt):
        A = list(set(sk['B'])-set(ctt['policy']))
        a = []; z = 1
        for attrs in A:
            a.append(group.hash(attrs, ZR))
        (indices,coeff_mult) = Zero_poly(a,len(a)-1,[0],[1])
        Coeffs = list(reversed(coeff_mult))
        for i in range(len(indices)-1):
            z *= pk['h_i'][i] ** Coeffs[i+1]
        V = (pair(ctt['C1prime'],z) * pair(sk['dk'],ctt['C2prime']))
        return ctt['Cprime'] * (V**(-1/Coeffs[0]))



def start_bench(group):
    group.InitBenchmark()
    group.StartBenchmark(["RealTime"])

def end_bench(group):
    group.EndBenchmark()
    benchmarks = group.GetGeneralBenchmarks()
    real_time = benchmarks['RealTime']
    return real_time


groupObj = PairingGroup('BN254')
cpabe = CPabe_SP21(groupObj)
PoK = PoK(groupObj)

def run_round_trip(n):
    result=[n]
    # RA setup
    U = ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN'] * n
    Setup_time = 0
    for i in range(50):
        start_bench(groupObj)
        (pk, mk) = cpabe.RAgen(len(U), U)
        Setup_time += end_bench(groupObj)
    result.append(Setup_time*20)

    # SA setup\
    SA_time=0
    for i in range(50):
        start_bench(groupObj)
        (sgk,vk) = cpabe.SAgen(pk)
        SA_time += end_bench(groupObj)
    result.append(SA_time*20)
    public_key_size = sum([len(x) for x in serializeDict(pk, groupObj).values()]) + sum([len(x) for x in serializeDict(vk, groupObj).values()])
    result.append(public_key_size)

    # Encryption key generation
    P = ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE']*n
    EncKGen_time = 0
    for i in range(50):
        start_bench(groupObj)
        (ek,sign) = cpabe.EncKGen(pk, sgk, vk, P, U)
        EncKGen_time += end_bench(groupObj)
    result.append(EncKGen_time*20)
    Enc_key_size = sum([len(x) for x in serializeDict(ek, groupObj).values()]) + sum([len(x) for x in serializeDict(sign, groupObj).values()])
    result.append(Enc_key_size)

    # Decryption key generation
    B = ['ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX']*n
    DecKGen_time = 0
    for i in range(50):
        start_bench(groupObj)
        dk = cpabe.DecKGen(pk, mk, B, U)
        DecKGen_time += end_bench(groupObj)
    result.append(DecKGen_time*20)
    Dec_key_size = sum([len(x) for x in serializeDict(dk, groupObj).values()])
    result.append(Dec_key_size)

    # Encryption
    rand_msg = groupObj.random(GT)
    encrypt_time = 0
    for i in range(50):
        start_bench(groupObj)
        (ct, Rand) = cpabe.encrypt(pk, vk, rand_msg, ek, sign, P)
        encrypt_time += end_bench(groupObj)
    result.append(encrypt_time*20)
    Cipher_size = sum([len(x) for x in serializeDict(ct, groupObj).values()]) + sum([len(x) for x in serializeDict(Rand, groupObj).values()])
    result.append(Cipher_size)

    # Sanitization
    Sanitization_time = 0
    for i in range(50):
        start_bench(groupObj)
        (ctt) = cpabe.Sanitization(pk, vk, ct, Rand)
        Sanitization_time += end_bench(groupObj)
    result.append(Sanitization_time*20)
    San_Cipher_size = sum([len(x) for x in serializeDict(ctt, groupObj).values()])
    result.append(San_Cipher_size)
    # Decryption
    decrypt_time = 0
    for i in range(50):
        start_bench(groupObj)
        rec_msg = cpabe.decrypt(pk, dk, ctt)
        decrypt_time += end_bench(groupObj)
    result.append(decrypt_time * 20)
    return result

book=Workbook()
data=book.active
title=["n","setup_time","SA_time", "public_key_size", "EncKGen_time", "Enc_key_size" ,"DecKGen_time", "Dec_key_size","encrypt_time","Cipher_size","Sanitize_time","San_Cipher_size ","Decryption_time"]
data.append(title)

for n in range(1,50):
    data.append(run_round_trip(n))
    print(n)

book.save("Result.xlsx")