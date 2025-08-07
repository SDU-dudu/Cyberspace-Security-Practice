import math
from math import gcd
import hashlib

# SM2参数 (256位素数域)
p = 0x8542D69E4C044F18E8B92435BF6FF7DE457283915C45517D722EDB8B08F1DFC3
a = 0x787968B4FA32C3FD2417842E73BBFEFF2F3C848B6831D7E0EC65228B3937E498
b = 0x63E4C6D3B23B0C849CF84241484BFE48F61D59A5B16BA06E6E12D1DA27C5249A
n = 0x8542D69E4C044F18E8B92435BF6FF7DD297720630485628D5AE74EE7C32E79B7
Gx = 0x421DEBD61B62EAB6746434EBC3CC315E32220B3BADD50BDC4C4E6C147FEDD43D
Gy = 0x0680512BCBB42C07D47349D2153B70C4E5D7FDFCBFA36EA1A85841B9E46E09A2

def generate(m, n):  # 从 m 生成一个椭圆曲线签名所需的整数 e
    tmp = hashlib.sha256(m.encode()).digest()
    return int.from_bytes(tmp, 'big') % n

def mul_inv(a, m):  # 计算 a 在模 m 下的乘法逆元
    if math.gcd(a, m) != 1:
        return None
    return pow(a, -1, m)

def add(m, n):  # 曲线上的点加算法
    temp = []
    if m == 0:
        return n
    if n == 0:
        return m
    if m != n:
        denominator = (m[0] - n[0]) % p
        if denominator == 0:
            return 0
        k = ((m[1] - n[1]) * mul_inv(denominator, p)) % p
    else:
        denominator = (2 * m[1]) % p
        if denominator == 0:
            return 0
        k = ((3 * (m[0] ** 2) + a) * mul_inv(denominator, p)) % p
    x = (k ** 2 - m[0] - n[0]) % p
    y = (k * (m[0] - x) - m[1]) % p
    temp.append(x)
    temp.append(y)
    return temp

def p_mul_n(n, point):  # 椭圆曲线标量乘法
    result = 0
    temp = point.copy()
    while n > 0:
        if n % 2 == 1:
            result = add(result, temp)
        temp = add(temp, temp)
        n = n // 2
    return result

def ECDSA_sign(private_key, msg, k, e, n, G):  # ECDSA 签名生成
    R = p_mul_n(k, G)  # 临时公钥 R = k * G
    r = R[0] % n
    s = (mul_inv(k, n) * (e + private_key * r)) % n
    return r, s

def Schnorr_sign(msg, private_key, k, n, G):  # Schnorr 签名生成
    r = p_mul_n(k, G)  # 临时公钥计算
    e = int(hashlib.sha256((str(r[0]) + msg).encode()).hexdigest(), 16) % n
    s = (k + e * private_key) % n
    return r, s, e

if __name__ == '__main__':
    # 测试参数
    d1 = 0x123456789ABCDEF12  # 私钥 1
    d2 = 0xABCDEF123456789AB  # 私钥 2
    k = 0x11111111111111111111111111111111  # 随机数 k
    m1 = 'Hello World'
    m2 = 'This is SDU DUDU'

    # 生成摘要
    e1 = generate(m1, n)
    e2 = generate(m2, n)

    G = [Gx, Gy]  # 基点 G

    print("测试信息：")
    print(f"d1 = {d1}, d2 = {d2}")
    print(f"m1 = {m1}, m2 = {m2}\n")

    # 泄露 k 导致泄露 d1
    print("泄露 k 会导致泄露 d1：")
    R = p_mul_n(k, G)
    r1 = R[0] % n
    s1 = (mul_inv(k, n) * (e1 + d1 * r1)) % n
    d_recovered = (mul_inv(r1, n) * (k * s1 - e1)) % n
    print(f"恢复的私钥 d1: {d_recovered}")
    if d_recovered == d1:
        print("验证成功\n")
    else:
        print("验证失败\n")

    # 重用 k 导致泄露 d1
    print("重用 k 会导致泄露 d1：")
    r21 = R[0] % n
    s21 = (mul_inv(k, n) * (e1 + d1 * r21)) % n
    r22 = R[0] % n
    s22 = (mul_inv(k, n) * (e2 + d1 * r22)) % n
    numerator = (e1 - e2) % n
    denominator = (s21 - s22) % n
    if denominator == 0:
        print("无法恢复 k")
    else:
        k_recovered = (numerator * mul_inv(denominator, n)) % n
        d_recovered = (mul_inv(r21, n) * (k_recovered * s21 - e1)) % n
        print(f"恢复的私钥 d1: {d_recovered}")
        if d_recovered == d1:
            print("验证成功\n")
        else:
            print("验证失败\n")

    print("两用户利用 k，推测彼此私钥 d：")
    r31, s31 = ECDSA_sign(d1, m1, k, e1, n, G)
    r32, s32 = ECDSA_sign(d2, m2, k, e2, n, G)

    # 由于k相同，r31和r32应该相等
    r_val = r31  # 使用共同的r值

    # 用户1用自己的私钥d1恢复k
    k1 = (e1 + d1 * r_val) * mul_inv(s31, n) % n
    # 用户1用恢复的k计算用户2的私钥d2
    d2_recovered = (s32 * k1 - e2) * mul_inv(r_val, n) % n

    # 用户2用自己的私钥d2恢复k
    k2 = (e2 + d2 * r_val) * mul_inv(s32, n) % n
    # 用户2用恢复的k计算用户1的私钥d1
    d1_recovered = (s31 * k2 - e1) * mul_inv(r_val, n) % n

    print(f"恢复的私钥 d1: {d1_recovered}, d2: {d2_recovered}")
    print(f"原始私钥 d1: {d1}, d2: {d2}")
    if d1_recovered == d1 and d2_recovered == d2:
        print("验证成功\n")
    else:
        print("验证失败\n")

    # 使用相同的 d 和 k 会导致泄露 d1
    print("使用相同的 d 和 k 会导致泄露 d1：")
    r41, s41 = ECDSA_sign(d1, m1, k, e1, n, G)
    r42, s42, e42 = Schnorr_sign(m1, d1, k, n, G)
    numerator = (s42 * s41 - e1) % n
    denominator = (r41 + e42 * s41) % n
    if denominator == 0:
        print("无法恢复私钥")
    else:
        d_recovered = (numerator * mul_inv(denominator, n)) % n
        print(f"恢复的私钥 d1: {d_recovered}")
        if d_recovered == d1:
            print("验证成功\n")
        else:
            print("验证失败\n")
