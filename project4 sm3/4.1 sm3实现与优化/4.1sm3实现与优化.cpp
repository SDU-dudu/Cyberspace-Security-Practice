#include <iostream>
#include <vector>
#include <iomanip>
#include <cstring>
#include <chrono>

using namespace std;

typedef uint32_t u32;
typedef uint8_t u8;

// 共同的辅助函数
vector<u8> string_to_bytes(const string& str) {
    return vector<u8>(str.begin(), str.end());
}

vector<u8> message_padding(const vector<u8>& msg) {
    size_t len = msg.size() * 8;
    vector<u8> padded = msg;

    padded.push_back(0x80);
    while ((padded.size() * 8) % 512 != 448)
        padded.push_back(0x00);

    for (int i = 7; i >= 0; --i)
        padded.push_back((u8)((len >> (i * 8)) & 0xFF));

    return padded;
}

void init_T(u32 T[64]) {
    for (int i = 0; i < 64; ++i)
        T[i] = (i < 16) ? 0x79CC4519 : 0x7A879D8A;
}

u32 left_rotate(u32 x, u32 n) {
    return (x << n) | (x >> (32 - n));
}

u32 P0(u32 x) {
    return x ^ left_rotate(x, 9) ^ left_rotate(x, 17);
}

u32 P1(u32 x) {
    return x ^ left_rotate(x, 15) ^ left_rotate(x, 23);
}

void message_expansion(const u8* block, u32 W[68], u32 W1[64]) {
    for (int i = 0; i < 16; ++i) {
        W[i] = (block[4 * i] << 24) |
            (block[4 * i + 1] << 16) |
            (block[4 * i + 2] << 8) |
            (block[4 * i + 3]);
    }

    for (int i = 16; i < 68; ++i) {
        u32 tmp = P1(W[i - 16] ^ W[i - 9] ^ left_rotate(W[i - 3], 15));
        W[i] = tmp ^ left_rotate(W[i - 13], 7) ^ W[i - 6];
    }

    for (int i = 0; i < 64; ++i)
        W1[i] = W[i] ^ W[i + 4];
}

void compression(u32 V[8], const u8* block, u32 T[64]) {
    u32 W[68], W1[64];
    message_expansion(block, W, W1);

    u32 A = V[0], B = V[1], C = V[2], D = V[3];
    u32 E = V[4], F = V[5], G = V[6], H = V[7];

    for (int j = 0; j < 64; ++j) {
        u32 SS1 = left_rotate((left_rotate(A, 12) + E + left_rotate(T[j], j % 32)) & 0xFFFFFFFF, 7);
        u32 SS2 = SS1 ^ left_rotate(A, 12);
        u32 TT1 = ((j < 16) ? (A ^ B ^ C) : ((A & B) | (A & C) | (B & C))) + D + SS2 + W1[j];
        u32 TT2 = ((j < 16) ? (E ^ F ^ G) : ((E & F) | (~E & G))) + H + SS1 + W[j];

        D = C;
        C = left_rotate(B, 9);
        B = A;
        A = TT1;
        H = G;
        G = left_rotate(F, 19);
        F = E;
        E = P0(TT2);
    }

    V[0] ^= A; V[1] ^= B; V[2] ^= C; V[3] ^= D;
    V[4] ^= E; V[5] ^= F; V[6] ^= G; V[7] ^= H;
}

// 基本版本
vector<u8> sm3_hash_base(const string& input) {
    u32 T[64];
    init_T(T);

    u32 V[8] = {
        0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600,
        0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E
    };

    vector<u8> msg_bytes = string_to_bytes(input);
    vector<u8> padded = message_padding(msg_bytes);

    size_t block_count = padded.size() / 64;
    for (size_t i = 0; i < block_count; ++i) {
        compression(V, &padded[i * 64], T);
    }

    vector<u8> hash_result;
    for (int i = 0; i < 8; ++i) {
        hash_result.push_back((V[i] >> 24) & 0xFF);
        hash_result.push_back((V[i] >> 16) & 0xFF);
        hash_result.push_back((V[i] >> 8) & 0xFF);
        hash_result.push_back(V[i] & 0xFF);
    }

    return hash_result;
}

// 优化版本1
vector<u8> sm3_hash_opt1(const string& input) {
    static const u32 T[64] = {
        0x79CC4519,0x79CC4519,0x79CC4519,0x79CC4519,
        0x79CC4519,0x79CC4519,0x79CC4519,0x79CC4519,
        0x79CC4519,0x79CC4519,0x79CC4519,0x79CC4519,
        0x79CC4519,0x79CC4519,0x79CC4519,0x79CC4519,
        0x7A879D8A,0x7A879D8A,0x7A879D8A,0x7A879D8A,
        0x7A879D8A,0x7A879D8A,0x7A879D8A,0x7A879D8A,
        0x7A879D8A,0x7A879D8A,0x7A879D8A,0x7A879D8A,
        0x7A879D8A,0x7A879D8A,0x7A879D8A,0x7A879D8A,
        0x7A879D8A,0x7A879D8A,0x7A879D8A,0x7A879D8A,
        0x7A879D8A,0x7A879D8A,0x7A879D8A,0x7A879D8A,
        0x7A879D8A,0x7A879D8A,0x7A879D8A,0x7A879D8A,
        0x7A879D8A,0x7A879D8A,0x7A879D8A,0x7A879D8A,
        0x7A879D8A,0x7A879D8A,0x7A879D8A,0x7A879D8A,
        0x7A879D8A,0x7A879D8A,0x7A879D8A,0x7A879D8A,
        0x7A879D8A,0x7A879D8A,0x7A879D8A,0x7A879D8A,
        0x7A879D8A,0x7A879D8A,0x7A879D8A,0x7A879D8A
    };

    u32 V[8] = {
        0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600,
        0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E
    };

    vector<u8> msg_bytes = string_to_bytes(input);
    vector<u8> padded = message_padding(msg_bytes);
    size_t block_count = padded.size() / 64;

    for (size_t i = 0; i < block_count; ++i) {
        u32 W[68], W1[64];
        message_expansion(&padded[i * 64], W, W1);

        u32 A = V[0], B = V[1], C = V[2], D = V[3];
        u32 E = V[4], F = V[5], G = V[6], H = V[7];

        for (int j = 0; j < 64; ++j) {
            u32 SS1 = left_rotate((left_rotate(A, 12) + E + left_rotate(T[j], j % 32)) & 0xFFFFFFFF, 7);
            u32 SS2 = SS1 ^ left_rotate(A, 12);
            u32 TT1 = ((j < 16) ? (A ^ B ^ C) : ((A & B) | (A & C) | (B & C))) + D + SS2 + W1[j];
            u32 TT2 = ((j < 16) ? (E ^ F ^ G) : ((E & F) | (~E & G))) + H + SS1 + W[j];

            D = C;
            C = left_rotate(B, 9);
            B = A;
            A = TT1;
            H = G;
            G = left_rotate(F, 19);
            F = E;
            E = P0(TT2);
        }

        V[0] ^= A; V[1] ^= B; V[2] ^= C; V[3] ^= D;
        V[4] ^= E; V[5] ^= F; V[6] ^= G; V[7] ^= H;
    }

    vector<u8> hash_result;
    for (int i = 0; i < 8; ++i) {
        hash_result.push_back((V[i] >> 24) & 0xFF);
        hash_result.push_back((V[i] >> 16) & 0xFF);
        hash_result.push_back((V[i] >> 8) & 0xFF);
        hash_result.push_back(V[i] & 0xFF);
    }

    return hash_result;
}

// 优化版本2
vector<u8> sm3_hash_opt2(const string& input) {
    u32 T[64];
    init_T(T);

    u32 V[8] = {
        0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600,
        0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E
    };

    vector<u8> msg_bytes = string_to_bytes(input);
    vector<u8> padded = message_padding(msg_bytes);
    size_t block_count = padded.size() / 64;

    for (size_t i = 0; i < block_count; ++i) {
        u32 W[68], W1[64];
        message_expansion(&padded[i * 64], W, W1);

        u32 A = V[0], Bv = V[1], C = V[2], D = V[3];
        u32 E = V[4], F = V[5], G = V[6], H = V[7];

        for (int j = 0; j < 64; ++j) {
            u32 SS1 = left_rotate((left_rotate(A, 12) + E + left_rotate(T[j], j % 32)) & 0xFFFFFFFF, 7);
            u32 SS2 = SS1 ^ left_rotate(A, 12);
            u32 TT1 = ((j < 16) ? (A ^ Bv ^ C) : ((A & Bv) | (A & C) | (Bv & C))) + D + SS2 + W1[j];
            u32 TT2 = ((j < 16) ? (E ^ F ^ G) : ((E & F) | ((~E) & G))) + H + SS1 + W[j];

            D = C;
            C = left_rotate(Bv, 9);
            Bv = A;
            A = TT1;
            H = G;
            G = left_rotate(F, 19);
            F = E;
            E = P0(TT2);
        }

        V[0] ^= A; V[1] ^= Bv; V[2] ^= C; V[3] ^= D;
        V[4] ^= E; V[5] ^= F; V[6] ^= G; V[7] ^= H;
    }

    vector<u8> hash_result;
    for (int i = 0; i < 8; ++i) {
        hash_result.push_back((V[i] >> 24) & 0xFF);
        hash_result.push_back((V[i] >> 16) & 0xFF);
        hash_result.push_back((V[i] >> 8) & 0xFF);
        hash_result.push_back(V[i] & 0xFF);
    }

    return hash_result;
}

// 优化版本3
vector<u8> sm3_hash_opt3(const string& input) {
    u32 T[64];
    init_T(T);

    u32 V[8] = {
        0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600,
        0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E
    };

    vector<u8> msg_bytes = string_to_bytes(input);
    vector<u8> padded = message_padding(msg_bytes);
    size_t block_count = padded.size() / 64;

    for (size_t i = 0; i < block_count; ++i) {
        u32 W[68], W1[64];
        message_expansion(&padded[i * 64], W, W1);

        u32 A = V[0], B = V[1], C = V[2], D = V[3];
        u32 E = V[4], F = V[5], G = V[6], H = V[7];

        for (int j = 0; j < 64; ++j) {
            u32 SS1 = left_rotate((left_rotate(A, 12) + E + left_rotate(T[j], j % 32)) & 0xFFFFFFFF, 7);
            u32 SS2 = SS1 ^ left_rotate(A, 12);
            u32 TT1 = ((j < 16) ? (A ^ B ^ C) : ((A & B) | (A & C) | (B & C))) + D + SS2 + W1[j];
            u32 TT2 = ((j < 16) ? (E ^ F ^ G) : ((E & F) | ((~E) & G))) + H + SS1 + W[j];

            D = C;
            C = left_rotate(B, 9);
            B = A;
            A = TT1;
            H = G;
            G = left_rotate(F, 19);
            F = E;
            E = P0(TT2);
        }

        V[0] ^= A; V[1] ^= B; V[2] ^= C; V[3] ^= D;
        V[4] ^= E; V[5] ^= F; V[6] ^= G; V[7] ^= H;
    }

    vector<u8> hash_result;
    for (int i = 0; i < 8; ++i) {
        hash_result.push_back((V[i] >> 24) & 0xFF);
        hash_result.push_back((V[i] >> 16) & 0xFF);
        hash_result.push_back((V[i] >> 8) & 0xFF);
        hash_result.push_back(V[i] & 0xFF);
    }

    return hash_result;
}

// 优化版本4
vector<u8> sm3_hash_opt4(const string& input) {
    u32 T[64];
    init_T(T);

    u32 V[8] = {
        0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600,
        0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E
    };

    vector<u8> msg_bytes = string_to_bytes(input);
    vector<u8> padded = message_padding(msg_bytes);
    size_t block_count = padded.size() / 64;

    for (size_t i = 0; i < block_count; ++i) {
        u32 W[68], W1[64];
        message_expansion(&padded[i * 64], W, W1);

        u32 A = V[0], B = V[1], C = V[2], D = V[3];
        u32 E = V[4], F = V[5], G = V[6], H = V[7];

        for (int j = 0; j < 64; ++j) {
            u32 SS1 = left_rotate((left_rotate(A, 12) + E + left_rotate(T[j], j % 32)) & 0xFFFFFFFF, 7);
            u32 SS2 = SS1 ^ left_rotate(A, 12);
            u32 TT1 = ((j < 16) ? (A ^ B ^ C) : ((A & B) | (A & C) | (B & C))) + D + SS2 + W1[j];
            u32 TT2 = ((j < 16) ? (E ^ F ^ G) : ((E & F) | ((~E) & G))) + H + SS1 + W[j];

            D = C;
            C = left_rotate(B, 9);
            B = A;
            A = TT1;
            H = G;
            G = left_rotate(F, 19);
            F = E;
            E = P0(TT2);
        }

        V[0] ^= A; V[1] ^= B; V[2] ^= C; V[3] ^= D;
        V[4] ^= E; V[5] ^= F; V[6] ^= G; V[7] ^= H;
    }

    vector<u8> hash_result;
    for (int i = 0; i < 8; ++i) {
        hash_result.push_back((V[i] >> 24) & 0xFF);
        hash_result.push_back((V[i] >> 16) & 0xFF);
        hash_result.push_back((V[i] >> 8) & 0xFF);
        hash_result.push_back(V[i] & 0xFF);
    }

    return hash_result;
}

int main() {
    string input = "Hollow world! This is SDU DUDU!";

    // 测试基本版本
    auto start = chrono::high_resolution_clock::now();
    vector<u8> hash_baseline = sm3_hash_base(input);
    auto end = chrono::high_resolution_clock::now();
    chrono::duration<double, milli> duration_baseline = end - start;

    // 测试优化版本1
    start = chrono::high_resolution_clock::now();
    vector<u8> hash_opt1 = sm3_hash_opt1(input);
    end = chrono::high_resolution_clock::now();
    chrono::duration<double, milli> duration_opt1 = end - start;

    // 测试优化版本2
    start = chrono::high_resolution_clock::now();
    vector<u8> hash_opt2 = sm3_hash_opt2(input);
    end = chrono::high_resolution_clock::now();
    chrono::duration<double, milli> duration_opt2 = end - start;

    // 测试优化版本3
    start = chrono::high_resolution_clock::now();
    vector<u8> hash_opt3 = sm3_hash_opt3(input);
    end = chrono::high_resolution_clock::now();
    chrono::duration<double, milli> duration_opt3 = end - start;

    // 测试优化版本4
    start = chrono::high_resolution_clock::now();
    vector<u8> hash_opt4 = sm3_hash_opt4(input);
    end = chrono::high_resolution_clock::now();
    chrono::duration<double, milli> duration_opt4 = end - start;

    // 输出结果
    cout << "SM3(\"" << input << "\") - Base: ";
    for (u8 byte : hash_baseline)
        cout << hex << setw(2) << setfill('0') << (int)byte;
    cout << endl
        << "Time: " << duration_baseline.count() << " ms" << endl;

    cout << "SM3(\"" << input << "\") - Opt1: ";
    for (u8 byte : hash_opt1)
        cout << hex << setw(2) << setfill('0') << (int)byte;
    cout << endl
        << "Time: " << duration_opt1.count() << " ms" << endl;

    cout << "SM3(\"" << input << "\") - Opt2: ";
    for (u8 byte : hash_opt2)
        cout << hex << setw(2) << setfill('0') << (int)byte;
    cout << endl
        << "Time: " << duration_opt2.count() << " ms" << endl;

    cout << "SM3(\"" << input << "\") - Opt3: ";
    for (u8 byte : hash_opt3)
        cout << hex << setw(2) << setfill('0') << (int)byte;
    cout << endl
        << "Time: " << duration_opt3.count() << " ms" << endl;

    cout << "SM3(\"" << input << "\") - Opt4: ";
    for (u8 byte : hash_opt4)
        cout << hex << setw(2) << setfill('0') << (int)byte;
    cout << endl
        << "Time: " << duration_opt4.count() << " ms" << endl;

    return 0;
}