#include <iostream>
#include <vector>
#include <iomanip>
#include <cstring>
#include <string>
#include <sstream>

using namespace std;

typedef uint32_t u32;
typedef uint8_t u8;
typedef vector<u8> Bytes;

u32 T[64];

void init_T() {
    for (int i = 0; i < 64; ++i) {
        T[i] = (i < 16) ? 0x79CC4519 : 0x7A879D8A;
    }
}

u32 left_rotate(u32 x, u32 n) {
    return (x << n) | (x >> (32 - n));
}

u32 FF(u32 x, u32 y, u32 z, int j) {
    return (j < 16) ? (x ^ y ^ z) : ((x & y) | (x & z) | (y & z));
}

u32 GG(u32 x, u32 y, u32 z, int j) {
    return (j < 16) ? (x ^ y ^ z) : ((x & y) | (~x & z));
}

u32 P0(u32 x) {
    return x ^ left_rotate(x, 9) ^ left_rotate(x, 17);
}

u32 P1(u32 x) {
    return x ^ left_rotate(x, 15) ^ left_rotate(x, 23);
}

Bytes string_to_Bytes(const string& str) {
    return Bytes(str.begin(), str.end());
}

Bytes message_padding(Bytes msg) {
    size_t len = msg.size() * 8;
    msg.push_back(0x80);
    while ((msg.size() * 8) % 512 != 448)
        msg.push_back(0x00);

    for (int i = 7; i >= 0; --i)
        msg.push_back((u8)((len >> (i * 8)) & 0xFF));

    return msg;
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

    for (int i = 0; i < 64; ++i) {
        W1[i] = W[i] ^ W[i + 4];
    }
}

void compression(u32 V[8], const u8* block) {
    u32 W[68], W1[64];
    message_expansion(block, W, W1);

    u32 A = V[0], B = V[1], C = V[2], D = V[3];
    u32 E = V[4], F = V[5], G = V[6], H = V[7];

    for (int j = 0; j < 64; ++j) {
        u32 SS1 = left_rotate((left_rotate(A, 12) + E + left_rotate(T[j], j % 32)) & 0xFFFFFFFF, 7);
        u32 SS2 = SS1 ^ left_rotate(A, 12);
        u32 TT1 = (FF(A, B, C, j) + D + SS2 + W1[j]) & 0xFFFFFFFF;
        u32 TT2 = (GG(E, F, G, j) + H + SS1 + W[j]) & 0xFFFFFFFF;

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

Bytes sm3_hash(const string& input) {
    init_T();

    u32 V[8] = {
        0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600,
        0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E
    };

    Bytes msg_bytes = string_to_Bytes(input);
    Bytes padded = message_padding(msg_bytes);

    size_t block_count = padded.size() / 64;

    for (size_t i = 0; i < block_count; ++i) {
        compression(V, &padded[i * 64]);
    }

    Bytes hash_result;
    for (int i = 0; i < 8; ++i) {
        hash_result.push_back((V[i] >> 24) & 0xFF);
        hash_result.push_back((V[i] >> 16) & 0xFF);
        hash_result.push_back((V[i] >> 8) & 0xFF);
        hash_result.push_back(V[i] & 0xFF);
    }

    return hash_result;
}

// Merkle树相关函数

Bytes concat_Bytes(const Bytes& a, const Bytes& b) {
    Bytes res = a;
    res.insert(res.end(), b.begin(), b.end());
    return res;
}

string Bytes_to_hex(const Bytes& b) {
    stringstream ss;
    ss << hex << setfill('0');
    for (auto x : b) ss << setw(2) << (int)x;
    return ss.str();
}

Bytes hash_leaf(const string& data) {
    string prefixed = "\x00" + data;
    return sm3_hash(prefixed);
}

Bytes hash_node(const Bytes& left, const Bytes& right) {
    Bytes prefix = { 0x01 };
    Bytes combined = prefix;
    combined.insert(combined.end(), left.begin(), left.end());
    combined.insert(combined.end(), right.begin(), right.end());
    return sm3_hash(string(combined.begin(), combined.end()));
}

vector<vector<Bytes>> build_merkle_tree(const vector<string>& leaves_data) {
    vector<Bytes> level;
    level.reserve(leaves_data.size());
    for (auto& d : leaves_data)
        level.push_back(hash_leaf(d));

    vector<vector<Bytes>> tree;
    tree.push_back(level);

    while (level.size() > 1) {
        vector<Bytes> next_level;
        int n = (int)level.size();
        next_level.reserve((n + 1) / 2);
        for (int i = 0; i < n; i += 2) {
            if (i + 1 == n) {
                next_level.push_back(level[i]);
            }
            else {
                next_level.push_back(hash_node(level[i], level[i + 1]));
            }
        }
        tree.push_back(next_level);
        level = move(next_level);
    }
    return tree;
}

vector<Bytes> generate_inclusion_proof(const vector<vector<Bytes>>& tree, size_t leaf_index) {
    vector<Bytes> proof;
    size_t index = leaf_index;
    for (size_t level = 0; level + 1 < tree.size(); ++level) {
        size_t sibling_index = (index % 2 == 0) ? index + 1 : index - 1;
        if (sibling_index < tree[level].size())
            proof.push_back(tree[level][sibling_index]);
        else
            proof.push_back({});
        index /= 2;
    }
    return proof;
}

bool verify_inclusion_proof(const string& leaf_data, const vector<Bytes>& proof, const Bytes& root, size_t leaf_index) {
    Bytes hash = hash_leaf(leaf_data);
    size_t idx = leaf_index;
    for (auto& sibling_hash : proof) {
        if (sibling_hash.empty()) {
        }
        else {
            if (idx % 2 == 0)
                hash = hash_node(hash, sibling_hash);
            else
                hash = hash_node(sibling_hash, hash);
        }
        idx /= 2;
    }
    return hash == root;
}

int main() {
    const size_t NUM_LEAVES = 100000;


    cout << "构建包含" << NUM_LEAVES << "个叶子节点的Merkle树..." << endl;

    // 生成叶子节点数据
    vector<string> leaves_data;
    leaves_data.reserve(NUM_LEAVES);
    for (size_t i = 0; i < NUM_LEAVES; ++i) {
        leaves_data.push_back("叶子数据 " + to_string(i));
    }

    // 构建Merkle树
    auto merkle_tree = build_merkle_tree(leaves_data);

    // 获取根哈希
    Bytes root_hash = merkle_tree.back()[0];
    cout << "Merkle树构建完成，根哈希为: " << Bytes_to_hex(root_hash) << endl << endl;

    // 存在性证明测试
    size_t test_index_exist = 99999;
    string test_leaf_exist = leaves_data[test_index_exist];
    auto proof_exist = generate_inclusion_proof(merkle_tree, test_index_exist);
    bool inclusion_exist = verify_inclusion_proof(test_leaf_exist, proof_exist, root_hash, test_index_exist);


    cout << "测试叶子索引: " << test_index_exist << endl;
    cout << "叶子数据: " << test_leaf_exist << endl;
    cout << "存在性证明验证结果: " << (inclusion_exist ? "通过" : "失败") << endl;
    cout << "该叶子节点存在于Merkle树中，存在性证明" << (inclusion_exist ? "有效" : "无效") << endl << endl;

    // 不存在性证明测试
    size_t test_index_nonexist = 100003;
    string test_leaf_nonexist = "叶子数据 " + to_string(test_index_nonexist);
    auto proof_nonexist = generate_inclusion_proof(merkle_tree, test_index_nonexist);
    bool inclusion_nonexist = false;
    if (test_index_nonexist < NUM_LEAVES) {
        inclusion_nonexist = verify_inclusion_proof(test_leaf_nonexist, proof_nonexist, root_hash, test_index_nonexist);
    }


    cout << "测试叶子索引: " << test_index_nonexist << endl;
    cout << "叶子数据: " << test_leaf_nonexist << endl;
    cout << "存在性证明验证结果: " << (inclusion_nonexist ? "通过" : "失败") << endl;
    cout << "该叶子节点不存在于Merkle树中，不存在性证明" << (!inclusion_nonexist ? "有效" : "无效") << endl;

    return 0;
}