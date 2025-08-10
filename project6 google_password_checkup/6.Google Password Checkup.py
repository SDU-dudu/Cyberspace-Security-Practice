import random
import hashlib
from phe import paillier
import gmpy2


class User:
    def __init__(self, pwd_list):
        self.pwd_list = pwd_list  # 用户密码集合
        self.k1 = None  # 用户私钥
        self.p = None  # 素数 p
        self.q = None  # 素数 q
        self.g = None  # 群生成元 g
        self.pub_key = None  # Paillier 公钥
        self.enc_pwd_list = None  # 加密并打乱后的密码列表
        self.enc_sum = None  # 交集元素标签的加密和

    def recv_pub_info(self, p, q, g, pub_key):
        self.p = p
        self.q = q
        self.g = g
        self.pub_key = pub_key
        self.k1 = random.randint(1, q - 1)  # 用户选择私钥 k1

    def round1(self):
        enc_pwd_list = []
        for pwd in self.pwd_list:
            h_val = self.hash_to_group(pwd)
            enc_pwd = pow(h_val, self.k1, self.p)
            enc_pwd_list.append(enc_pwd)
        random.shuffle(enc_pwd_list)  # 打乱顺序
        self.enc_pwd_list = enc_pwd_list
        return enc_pwd_list

    def recv_round2(self, enc_srv_pwd_list, srv_pwd_with_tags):
        self.enc_srv_pwd_list = set(enc_srv_pwd_list)  # 转换为集合便于快速查找
        self.srv_pwd_with_tags = srv_pwd_with_tags  # [(H(w_j)^k2, AEnc(t_j))]

    def round3(self):
        enc_tags = []
        for C_j, enc_tag in self.srv_pwd_with_tags:
            E_j = pow(C_j, self.k1, self.p)  # 计算 H(w_j)^(k1*k2)
            enc_tags.append((E_j, enc_tag))

        # 计算交集元素的索引
        intersection_indices = [i for i, (E_j, _) in enumerate(enc_tags) if E_j in self.enc_srv_pwd_list]

        # 同态求和
        if not intersection_indices:
            sum_enc = self.pub_key.encrypt(0)
        else:
            sum_enc = self.srv_pwd_with_tags[intersection_indices[0]][1]
            for idx in intersection_indices[1:]:
                sum_enc += self.srv_pwd_with_tags[idx][1]

        # 刷新密文：添加加密的 0
        self.enc_sum = sum_enc + self.pub_key.encrypt(0)
        return self.enc_sum

    def hash_to_group(self, s):
        h = hashlib.sha256(s.encode()).digest()
        x = int.from_bytes(h, 'big') % self.q
        return pow(self.g, x, self.p)


class Server:
    def __init__(self, leak_pwd_tags):
        self.leak_pwd_tags = leak_pwd_tags  # 泄露密码及其标签
        self.k2 = None  # 服务器私钥
        self.p = None  # 素数 p
        self.q = None  # 素数 q
        self.g = None  # 群生成元 g
        self.pub_key = None  # Paillier 公钥
        self.priv_key = None  # Paillier 私钥
        self.enc_pwd_list = None  # 接收到的用户加密密码列表
        self.intersection_sum = None  # 交集元素标签的总和

    def gen_pub_info(self, q_bits=256):
        # 生成安全素数 p = 2q + 1
        self.q = gmpy2.next_prime(random.getrandbits(q_bits))
        self.p = 2 * self.q + 1
        while not gmpy2.is_prime(self.p):
            self.q = gmpy2.next_prime(self.q)
            self.p = 2 * self.q + 1
        self.p = int(self.p)
        self.q = int(self.q)

        # 生成群生成元 g
        while True:
            h = random.randint(2, self.p - 2)
            self.g = pow(h, 2, self.p)
            if self.g != 1:
                break

        # 生成 Paillier 密钥对
        self.pub_key, self.priv_key = paillier.generate_paillier_keypair()

        return self.p, self.q, self.g, self.pub_key

    def recv_round1(self, enc_pwd_list):
        self.enc_pwd_list = enc_pwd_list
        self.k2 = random.randint(1, self.q - 1)  # 服务器选择私钥 k2

    def round2(self):
        # 计算加密密码列表 Z = [H(v_i)^(k1*k2)]
        enc_pwd_list = [pow(a, self.k2, self.p) for a in self.enc_pwd_list]
        random.shuffle(enc_pwd_list)

        # 计算带标签的加密密码列表 [(H(w_j)^k2, AEnc(t_j))]
        srv_pwd_with_tags = []
        for pwd, tag in self.leak_pwd_tags:
            h_val = self.hash_to_group(pwd)
            C_j = pow(h_val, self.k2, self.p)
            enc_tag = self.pub_key.encrypt(tag)
            srv_pwd_with_tags.append((C_j, enc_tag))
        random.shuffle(srv_pwd_with_tags)

        return enc_pwd_list, srv_pwd_with_tags

    def recv_round3(self, enc_intersection_sum):
        self.intersection_sum = self.priv_key.decrypt(enc_intersection_sum)

    def hash_to_group(self, s):
        h = hashlib.sha256(s.encode()).digest()
        x = int.from_bytes(h, 'big') % self.q
        return pow(self.g, x, self.p)


# 测试
if __name__ == "__main__":
    user_pwd_list = ["password1", "password2", "password3", "password4"]  # 用户的密码集合
    leak_pwd_tags = [("password1", 1), ("password3", 3), ("password4", 4), ("password6", 6)]  # 泄露密码及其标签

    user = User(user_pwd_list)
    server = Server(leak_pwd_tags)

    p, q, g, pub_key = server.gen_pub_info(q_bits=256)
    user.recv_pub_info(p, q, g, pub_key)

    enc_pwd_list = user.round1()
    server.recv_round1(enc_pwd_list)

    enc_srv_pwd_list, srv_pwd_with_tags = server.round2()
    user.recv_round2(enc_srv_pwd_list, srv_pwd_with_tags)

    enc_intersection_sum = user.round3()
    server.recv_round3(enc_intersection_sum)

    print("User's passwords:", user_pwd_list)
    print("Leaked passwords with tags:", leak_pwd_tags)
    print("Sum of tags for intersected passwords:", server.intersection_sum)