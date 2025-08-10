import random
import hashlib
import binascii
import time

# SM2椭圆曲线参数（示例）
P = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFF
A = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF00000000FFFFFFFFFFFFFFFC
B = 0x28E9FA9E9D9F5E344D5A9E4BCF6509A7F39789F515AB8F92DDBCBD414D940E93
N = 0xFFFFFFFEFFFFFFFFFFFFFFFFFFFFFFFF7203DF6B21C6052B53BBF40939D54123
Gx = 0x32C4AE2C1F1981195F9904466A39C9948FE30BBFF2660BE1715A4589334C74C7
Gy = 0xBC3736A2F4F6779C59BDCEE36B692153D0A9877CC62A474002DF32E52139F0A0


class SM2_Basic:
    def __init__(self):
        self.p = P
        self.a = A
        self.b = B
        self.n = N
        self.G = (Gx, Gy)

    # 模逆算法(扩展欧几里得)
    def _mod_inverse(self, a, p):
        old_r, r = a, p
        old_s, s = 1, 0
        while r != 0:
            quotient = old_r // r
            old_r, r = r, old_r - quotient * r
            old_s, s = s, old_s - quotient * s
        return old_s % p

    # 椭圆曲线点加
    def _point_add(self, P, Q):
        if P == (0, 0):
            return Q
        if Q == (0, 0):
            return P
        x1, y1 = P
        x2, y2 = Q

        if x1 == x2 and (y1 + y2) % self.p == 0:
            return (0, 0)
        if P == Q:
            l = (3 * x1 * x1 + self.a) * self._mod_inverse(2 * y1, self.p) % self.p
        else:
            l = (y2 - y1) * self._mod_inverse(x2 - x1, self.p) % self.p

        x3 = (l * l - x1 - x2) % self.p
        y3 = (l * (x1 - x3) - y1) % self.p
        return (x3, y3)

    # 椭圆曲线点乘
    def _point_mul(self, k, P):
        result = (0, 0)
        while k > 0:
            if k & 1:
                result = self._point_add(result, P)
            P = self._point_add(P, P)
            k >>= 1
        return result

    # SM2密钥对生成
    def generate_keypair(self):
        private_key = random.randint(1, self.n - 1)
        public_key = self._point_mul(private_key, self.G)
        return private_key, public_key

    # 密钥派生函数(基于SM3)
    def _kdf(self, Z, klen):
        ct = 0x00000001
        rcnt = (klen + 31) // 32
        output = b''
        for i in range(rcnt):
            ct_bytes = ct.to_bytes(4, 'big')
            hash_input = Z + ct_bytes
            sm3 = hashlib.new('sm3')
            sm3.update(hash_input)
            output += sm3.digest()
            ct += 1
        return output[:klen]

    # SM2加密
    def encrypt(self, public_key, msg):
        if isinstance(msg, str):
            msg = msg.encode()
        klen = len(msg)
        k = random.randint(1, self.n - 1)

        # 计算C1
        C1 = self._point_mul(k, self.G)
        C1_bytes = b'\x04' + C1[0].to_bytes(32, 'big') + C1[1].to_bytes(32, 'big')

        # 计算S
        S = self._point_mul(k, public_key)
        S_bytes = b'\x04' + S[0].to_bytes(32, 'big') + S[1].to_bytes(32, 'big')

        # 计算派生密钥
        Z = S_bytes
        t = self._kdf(Z, klen)
        if all(b == 0 for b in t):
            raise ValueError("KDF derived key is zero")

        # 计算密文C2
        C2 = bytes([m ^ t_i for m, t_i in zip(msg, t)])

        # 计算C3
        sm3 = hashlib.new('sm3')
        sm3.update(bytes([x for x in msg]))
        sm3.update(Z)
        C3 = sm3.digest()

        return C1_bytes + C3 + C2

    # SM2解密
    def decrypt(self, private_key, ciphertext):
        # 解析密文
        if ciphertext[0] != 0x04:
            raise ValueError("Invalid ciphertext format")
        C1 = (int.from_bytes(ciphertext[1:33], 'big'),
              int.from_bytes(ciphertext[33:65], 'big'))
        C3 = ciphertext[65:97]
        C2 = ciphertext[97:]
        klen = len(C2)

        # 计算椭圆曲线点S
        S = self._point_mul(private_key, C1)
        S_bytes = b'\x04' + S[0].to_bytes(32, 'big') + S[1].to_bytes(32, 'big')

        # 计算派生密钥
        Z = S_bytes
        t = self._kdf(Z, klen)
        if all(b == 0 for b in t):
            raise ValueError("KDF derived key is zero")

        # 解密消息
        msg = bytes([c ^ t_i for c, t_i in zip(C2, t)])

        # 验证C3
        sm3 = hashlib.new('sm3')
        sm3.update(msg)
        sm3.update(Z)
        u = sm3.digest()
        if u != C3:
            raise ValueError("Hash verification failed")

        return msg

    # SM2签名
    def sign(self, private_key, msg, ID=b'1234567812345678'):
        if isinstance(msg, str):
            msg = msg.encode()

        # 计算ZA
        entl = len(ID) * 8
        ENTL = entl.to_bytes(2, 'big')
        a_bytes = self.a.to_bytes(32, 'big')
        b_bytes = self.b.to_bytes(32, 'big')
        Gx_bytes = self.G[0].to_bytes(32, 'big')
        Gy_bytes = self.G[1].to_bytes(32, 'big')
        public_key = self._point_mul(private_key, self.G)
        Px_bytes = public_key[0].to_bytes(32, 'big')
        Py_bytes = public_key[1].to_bytes(32, 'big')

        sm3_za = hashlib.new('sm3')
        sm3_za.update(ENTL + ID + a_bytes + b_bytes + Gx_bytes + Gy_bytes + Px_bytes + Py_bytes)
        ZA = sm3_za.digest()

        # 计算e = Hv(ZA ∥ M)
        sm3_e = hashlib.new('sm3')
        sm3_e.update(ZA + msg)
        e = int.from_bytes(sm3_e.digest(), 'big')

        # 生成签名
        while True:
            k = random.randint(1, self.n - 1)
            x1, y1 = self._point_mul(k, self.G)
            r = (e + x1) % self.n
            if r == 0 or r + k == self.n:
                continue
            s = (self._mod_inverse(1 + private_key, self.n) * (k - r * private_key)) % self.n
            if s != 0:
                break

        return r.to_bytes(32, 'big') + s.to_bytes(32, 'big')

    # 签名验证
    def verify(self, public_key, msg, signature, ID=b'1234567812345678'):
        if isinstance(msg, str):
            msg = msg.encode()

        r = int.from_bytes(signature[:32], 'big')
        s = int.from_bytes(signature[32:], 'big')
        if not (1 <= r < self.n and 1 <= s < self.n):
            return False

        # 计算ZA
        entl = len(ID) * 8
        ENTL = entl.to_bytes(2, 'big')
        a_bytes = self.a.to_bytes(32, 'big')
        b_bytes = self.b.to_bytes(32, 'big')
        Gx_bytes = self.G[0].to_bytes(32, 'big')
        Gy_bytes = self.G[1].to_bytes(32, 'big')
        Px_bytes = public_key[0].to_bytes(32, 'big')
        Py_bytes = public_key[1].to_bytes(32, 'big')

        sm3_za = hashlib.new('sm3')
        sm3_za.update(ENTL + ID + a_bytes + b_bytes + Gx_bytes + Gy_bytes + Px_bytes + Py_bytes)
        ZA = sm3_za.digest()

        # 计算e
        sm3_e = hashlib.new('sm3')
        sm3_e.update(ZA + msg)
        e = int.from_bytes(sm3_e.digest(), 'big')

        t = (r + s) % self.n
        if t == 0:
            return False

        # 计算椭圆曲线点
        point1 = self._point_mul(s, self.G)
        point2 = self._point_mul(t, public_key)
        x1, y1 = self._point_add(point1, point2)

        R = (e + x1) % self.n
        return R == r

    def serialize_public_key(self, public_key):
        return b'\x04' + public_key[0].to_bytes(32, 'big') + public_key[1].to_bytes(32, 'big')


class SM2_Optimized:
    def __init__(self):
        self.p = P
        self.a = A
        self.b = B
        self.n = N
        self.G = (Gx, Gy)
        # 预计算G的雅可比坐标
        self.G_jacobian = (Gx, Gy, 1)

    # 模逆算法(扩展欧几里得)
    def _mod_inverse(self, a, p):
        old_r, r = a, p
        old_s, s = 1, 0
        while r != 0:
            quotient = old_r // r
            old_r, r = r, old_r - quotient * r
            old_s, s = s, old_s - quotient * s
        return old_s % p

    # 雅可比坐标下的点加倍运算
    def _jacobian_point_double(self, P):
        if P[2] == 0:  # 无穷远点
            return P

        X1, Y1, Z1 = P

        XX = (X1 * X1) % self.p
        YY = (Y1 * Y1) % self.p
        YYYY = (YY * YY) % self.p
        ZZ = (Z1 * Z1) % self.p
        S = 2 * ((X1 + YY) ** 2 - XX - YYYY) % self.p
        M = (3 * XX + self.a * (ZZ * ZZ) % self.p) % self.p
        T = (M * M - 2 * S) % self.p

        # 计算新坐标
        X3 = T
        Y3 = (M * (S - T) - 8 * YYYY) % self.p
        Z3 = ((Y1 + Z1) ** 2 - YY - ZZ) % self.p

        return (X3, Y3, Z3)

    # 雅可比坐标下的点加运算
    def _jacobian_point_add(self, P, Q):
        if P[2] == 0:  # P是无穷远点
            return Q
        if Q[2] == 0:  # Q是无穷远点
            return P

        X1, Y1, Z1 = P
        X2, Y2, Z2 = Q

        # 计算中间量
        Z1Z1 = (Z1 * Z1) % self.p
        Z2Z2 = (Z2 * Z2) % self.p
        U1 = (X1 * Z2Z2) % self.p
        U2 = (X2 * Z1Z1) % self.p
        S1 = (Y1 * Z2 * Z2Z2) % self.p
        S2 = (Y2 * Z1 * Z1Z1) % self.p

        H = (U2 - U1) % self.p
        R = (S2 - S1) % self.p

        if H == 0:
            if R == 0:
                return self._jacobian_point_double(P)
            return (0, 1, 0)  # 无穷远点

        # 计算中间量
        HH = (H * H) % self.p
        HHH = (H * HH) % self.p
        V = (U1 * HH) % self.p

        # 计算新坐标
        X3 = (R * R - HHH - 2 * V) % self.p
        Y3 = (R * (V - X3) - S1 * HHH) % self.p
        Z3 = (H * Z1 * Z2) % self.p

        return (X3, Y3, Z3)

    # 将雅可比坐标转换为仿射坐标
    def _from_jacobian(self, P):
        if P[2] == 0:  # 无穷远点
            return (0, 0)

        X, Y, Z = P
        Z_inv = self._mod_inverse(Z, self.p)
        Z_inv_sq = (Z_inv * Z_inv) % self.p
        x = (X * Z_inv_sq) % self.p
        y = (Y * Z_inv_sq * Z_inv) % self.p
        return (x, y)

    # 雅可比坐标点乘算法
    def _point_mul(self, k, P):
        # 处理无穷远点
        if P == (0, 0):
            return (0, 0)

        # 将仿射坐标转换为雅可比坐标
        if len(P) == 2:
            X, Y = P
            P_jac = (X, Y, 1)
        else:
            P_jac = P

        # 初始化结果为无穷远点
        result = (0, 1, 0)

        # 二进制展开
        while k > 0:
            if k & 1:
                result = self._jacobian_point_add(result, P_jac)
            k >>= 1
            if k > 0:
                P_jac = self._jacobian_point_double(P_jac)

        return self._from_jacobian(result)

    # SM2密钥对生成
    def generate_keypair(self):
        private_key = random.randint(1, self.n - 1)
        public_key = self._point_mul(private_key, self.G)
        return private_key, public_key

    # 密钥派生函数(基于SM3)
    def _kdf(self, Z, klen):
        ct = 0x00000001
        rcnt = (klen + 31) // 32
        output = b''
        for i in range(rcnt):
            ct_bytes = ct.to_bytes(4, 'big')
            hash_input = Z + ct_bytes
            sm3 = hashlib.new('sm3')
            sm3.update(hash_input)
            output += sm3.digest()
            ct += 1
        return output[:klen]

    # SM2加密
    def encrypt(self, public_key, msg):
        if isinstance(msg, str):
            msg = msg.encode()
        klen = len(msg)
        k = random.randint(1, self.n - 1)

        # 计算C1
        C1 = self._point_mul(k, self.G)
        C1_bytes = b'\x04' + C1[0].to_bytes(32, 'big') + C1[1].to_bytes(32, 'big')

        # 计算S
        S = self._point_mul(k, public_key)
        S_bytes = b'\x04' + S[0].to_bytes(32, 'big') + S[1].to_bytes(32, 'big')

        # 计算派生密钥
        Z = S_bytes
        t = self._kdf(Z, klen)
        if all(b == 0 for b in t):
            raise ValueError("KDF derived key is zero")

        # 计算密文C2
        C2 = bytes([m ^ t_i for m, t_i in zip(msg, t)])

        # 计算C3
        sm3 = hashlib.new('sm3')
        sm3.update(msg)
        sm3.update(Z)
        C3 = sm3.digest()

        return C1_bytes + C3 + C2

    # SM2解密
    def decrypt(self, private_key, ciphertext):
        # 解析密文
        if ciphertext[0] != 0x04:
            raise ValueError("Invalid ciphertext format")
        C1 = (int.from_bytes(ciphertext[1:33], 'big'),
              int.from_bytes(ciphertext[33:65], 'big'))
        C3 = ciphertext[65:97]
        C2 = ciphertext[97:]
        klen = len(C2)

        # 计算椭圆曲线点S
        S = self._point_mul(private_key, C1)
        S_bytes = b'\x04' + S[0].to_bytes(32, 'big') + S[1].to_bytes(32, 'big')

        # 计算派生密钥
        Z = S_bytes
        t = self._kdf(Z, klen)
        if all(b == 0 for b in t):
            raise ValueError("KDF derived key is zero")

        # 解密消息
        msg = bytes([c ^ t_i for c, t_i in zip(C2, t)])

        # 验证C3
        sm3 = hashlib.new('sm3')
        sm3.update(msg)
        sm3.update(Z)
        u = sm3.digest()
        if u != C3:
            raise ValueError("Hash verification failed")

        return msg

    # SM2签名
    def sign(self, private_key, msg, ID=b'1234567812345678'):
        if isinstance(msg, str):
            msg = msg.encode()

        # 计算ZA
        entl = len(ID) * 8
        ENTL = entl.to_bytes(2, 'big')
        a_bytes = self.a.to_bytes(32, 'big')
        b_bytes = self.b.to_bytes(32, 'big')
        Gx_bytes = self.G[0].to_bytes(32, 'big')
        Gy_bytes = self.G[1].to_bytes(32, 'big')
        public_key = self._point_mul(private_key, self.G)
        Px_bytes = public_key[0].to_bytes(32, 'big')
        Py_bytes = public_key[1].to_bytes(32, 'big')

        sm3_za = hashlib.new('sm3')
        sm3_za.update(ENTL + ID + a_bytes + b_bytes + Gx_bytes + Gy_bytes + Px_bytes + Py_bytes)
        ZA = sm3_za.digest()

        # 计算e = Hv(ZA ∥ M)
        sm3_e = hashlib.new('sm3')
        sm3_e.update(ZA + msg)
        e = int.from_bytes(sm3_e.digest(), 'big')

        # 生成签名
        while True:
            k = random.randint(1, self.n - 1)
            x1, y1 = self._point_mul(k, self.G)
            r = (e + x1) % self.n
            if r == 0 or r + k == self.n:
                continue
            s = (self._mod_inverse(1 + private_key, self.n) * (k - r * private_key)) % self.n
            if s != 0:
                break

        return r.to_bytes(32, 'big') + s.to_bytes(32, 'big')

    # 签名验证
    def verify(self, public_key, msg, signature, ID=b'1234567812345678'):
        if isinstance(msg, str):
            msg = msg.encode()

        r = int.from_bytes(signature[:32], 'big')
        s = int.from_bytes(signature[32:], 'big')
        if not (1 <= r < self.n and 1 <= s < self.n):
            return False

        # 计算ZA
        entl = len(ID) * 8
        ENTL = entl.to_bytes(2, 'big')
        a_bytes = self.a.to_bytes(32, 'big')
        b_bytes = self.b.to_bytes(32, 'big')
        Gx_bytes = self.G[0].to_bytes(32, 'big')
        Gy_bytes = self.G[1].to_bytes(32, 'big')
        Px_bytes = public_key[0].to_bytes(32, 'big')
        Py_bytes = public_key[1].to_bytes(32, 'big')

        sm3_za = hashlib.new('sm3')
        sm3_za.update(ENTL + ID + a_bytes + b_bytes + Gx_bytes + Gy_bytes + Px_bytes + Py_bytes)
        ZA = sm3_za.digest()

        # 计算e
        sm3_e = hashlib.new('sm3')
        sm3_e.update(ZA + msg)
        e = int.from_bytes(sm3_e.digest(), 'big')

        t = (r + s) % self.n
        if t == 0:
            return False

        # 使用雅可比坐标优化点加
        point1 = self._point_mul(s, self.G)
        point2 = self._point_mul(t, public_key)

        P1_jac = (point1[0], point1[1], 1)
        P2_jac = (point2[0], point2[1], 1)
        sum_jac = self._jacobian_point_add(P1_jac, P2_jac)
        x1, y1 = self._from_jacobian(sum_jac)

        R = (e + x1) % self.n
        return R == r

    def serialize_public_key(self, public_key):
        return b'\x04' + public_key[0].to_bytes(32, 'big') + public_key[1].to_bytes(32, 'big')


# 测试
if __name__ == "__main__":
    message = "Hello World! This is SDU DUDU!" * 10

    # 基本SM2测试
    print("基本SM2算法:")
    sm2_basic = SM2_Basic()
    private_key, public_key = sm2_basic.generate_keypair()

    # 加密
    start = time.time()
    ciphertext = sm2_basic.encrypt(public_key, message)
    end = time.time()
    print(f"基本SM2加密时间: {end - start:.4f} 秒")

    # 解密
    start = time.time()
    decrypted = sm2_basic.decrypt(private_key, ciphertext)
    end = time.time()
    print(f"基本SM2解密时间: {end - start:.4f} 秒")

    # 签名
    start = time.time()
    signature = sm2_basic.sign(private_key, message)
    end = time.time()
    print(f"基本SM2签名时间: {end - start:.4f} 秒")

    # 验证
    start = time.time()
    is_valid = sm2_basic.verify(public_key, message, signature)
    end = time.time()
    print(f"基本SM2验证时间: {end - start:.4f} 秒")
    print(f"基本SM2验证结果: {'成功' if is_valid else '失败'}\n")

    # 优化SM2测试
    print("优化SM2算法:")
    sm2_optimized = SM2_Optimized()
    private_key_opt, public_key_opt = sm2_optimized.generate_keypair()

    # 加密
    start = time.time()
    ciphertext_opt = sm2_optimized.encrypt(public_key_opt, message)
    end = time.time()
    print(f"优化SM2加密时间: {end - start:.4f} 秒")

    # 解密
    start = time.time()
    decrypted_opt = sm2_optimized.decrypt(private_key_opt, ciphertext_opt)
    end = time.time()
    print(f"优化SM2解密时间: {end - start:.4f} 秒")

    # 签名
    start = time.time()
    signature_opt = sm2_optimized.sign(private_key_opt, message)
    end = time.time()
    print(f"优化SM2签名时间: {end - start:.4f} 秒")

    # 验证
    start = time.time()
    is_valid_opt = sm2_optimized.verify(public_key_opt, message, signature_opt)
    end = time.time()
    print(f"优化SM2验证时间: {end - start:.4f} 秒")
    print(f"优化SM2验证结果: {'成功' if is_valid_opt else '失败'}")

    # 验证解密结果
    assert decrypted == message.encode(), "基本SM2解密结果与原始消息不一致"
    assert decrypted_opt == message.encode(), "优化SM2解密结果与原始消息不一致"
    print("\n所有测试验证成功!")