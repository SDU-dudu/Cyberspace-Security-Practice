import math
import random


# 辅助函数：生成与n互质的随机数
def choose_random_coprime(n):
    while True:
        val = random.randint(2, n - 1)
        if math.gcd(val, n) == 1:
            return val


# 曲线乘法逆元计算
def mul_inv(a, m):
    if math.gcd(a, m) != 1:
        return None
    return pow(a, -1, m)


# 曲线点加算法
def add(m, n):
    tmp = []
    if (m == 0):
        return n
    if (n == 0):
        return m  # 边界处理
    if (m != n):
        if (math.gcd(m[0] - n[0], p) != 1 and math.gcd(m[0] - n[0], p) != -1):
            return 0
        else:  # 斜率处理
            k = ((m[1] - n[1]) * mul_inv(m[0] - n[0], p)) % p
    else:
        k = ((3 * (m[0] * m[0]) + a) * mul_inv(2 * m[1], p)) % p
    x = (k * k - m[0] - n[0]) % p
    y = (k * (m[0] - x) - m[1]) % p
    tmp.append(x)
    tmp.append(y)
    return tmp


# 曲线标量乘法
def p_mul_n(n, p):
    if n == 1:
        return p
    tmp = p
    while (n >= 2):
        tmp = add(tmp, p)
        n = n - 1
    return tmp


# ECDSA签名算法
def ECDSA_sign(m, n, G, d, k):
    R = p_mul_n(k, G)
    r = R[0] % n
    e = hash(m)  # 摘要采用哈希生成
    s = (mul_inv(k, n) * (e + d * r)) % n
    return r, s


# ECDSA签名验证算法
def ECDSA_ver(m, n, G, r, s, P):
    e = hash(m)
    w = mul_inv(s, n)  # 本质为一种逆过程
    try:
        w_point = add(p_mul_n((e * w) % n, G), p_mul_n((r * w) % n, P))
        res = (w_point != 0) and (w_point[0] % n == r)
        return res
    except:
        print("模逆计算错误，请重试！")


# 未验证m的验证算法版本，用于测验伪造签名的有效性
def ver_no_m(e, n, G, r, s, P):
    w = mul_inv(s, n)
    v1 = (e * w) % n
    v2 = (r * w) % n
    w_point = add(p_mul_n(v1, G), p_mul_n(v2, P))
    if (w_point == 0):
        print('失败')
        return False
    else:
        if (w_point[0] % n == r):
            print('验证成功')
            return True


# satoshi无消息签名算法
def pretend(n, G, P):
    u = choose_random_coprime(n)
    v = choose_random_coprime(n)

    R = add(p_mul_n(u, G), p_mul_n(v, P))[0]
    e1 = (R * u * mul_inv(v, n)) % n
    s1 = (R * mul_inv(v, n)) % n

    print(f"\nu = {u}, v = {v}")
    print(f"计算得 R = {R},e1 = {e1}, s1 = {s1}")
    print(f"")

    ver_no_m(e1, n, G, R, s1, P)


# 曲线参数(大参数运行时间太慢，改为小参数用于伪造)
a = 1  # 曲线方程中的参数
b = 1  # 曲线方程中的参数
p = 23  # 有限域的大小，保持为质数
G = [5, 1]  # 基点
n = 21  # 曲线阶数，确保正确
d = 7  # 模拟私钥
k = choose_random_coprime(n)  # 随机数，用于签名
P = p_mul_n(d, G)  # 计算公钥

m1 = 'Hello World! This is SDU DUDU!'

# 计算签名
r, s = ECDSA_sign(m1, n, G, d, k)
print("签名结果为:", r, s)
print("验证结果为:", ECDSA_ver(m1, n, G, r, s, P), "\n")  # 签名正常验证，确保结果的有效性

print("伪装签名攻击：")
pretend(n, G, P)  # 无消息签名伪造攻击实施