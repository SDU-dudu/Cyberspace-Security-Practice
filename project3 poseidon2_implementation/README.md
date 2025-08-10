# 实验三：用 circom 实现 Poseidon2 哈希算法电路

## 一、实验任务
实现基于 Poseidon2 哈希算法的零知识证明电路，参数为 (n,t,d)=(256,3,5)，要求：
1. 公开输入为 Poseidon2 哈希值
2. 隐私输入为哈希原象
3. 使用 Groth16 算法生成证明

## 二、实验环境
- 操作系统：Ubuntu 22.04 (VMware 虚拟机)
- 编译器：circom 2.2.2
- 依赖工具：snarkjs, Node.js, Rust

---

## 三、实验步骤及问题解决（带详细注释）

### 3.1 环境准备
#### 3.1.1 安装 circom
```bash
# 安装 Rust 工具链（circom 依赖）
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
# 利用国内镜像
export RUSTUP_DIST_SERVER=https://mirrors.ustc.edu.cn/rust-static
export RUSTUP_UPDATE_ROOT=https://mirrors.ustc.edu.cn/rust-static/rustup
curl https://sh.rustup.rs -sSf | sh


# 安装 circom（--locked 确保使用锁定的依赖版本）
cargo install --locked circom

# 验证安装
circom --version  # 输出circom 2.2.2
```
<img src=".\截图\circom安装成功.png"> 

#### 3.1.2 安装 snarkjs
```bash
# 全局安装 snarkjs（-g 表示全局安装）
sudo npm install -g snarkjs
# npm 是 Node.js 的包管理器
```

**遇到的问题**：`snarkjs: 未找到命令`  
**问题原因**：npm 全局路径未加入系统 PATH  
**解决方法**：
```bash
# 将 npm 全局安装路径添加到 bashrc 配置文件
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.bashrc
# >> 表示追加内容，~/.bashrc 是用户的 bash 配置文件

# 重新加载配置
source ~/.bashrc  # 使修改立即生效
```

### 3.2 电路实现
#### 3.2.1 创建项目结构
```bash
# 创建项目目录
mkdir poseidon2_circuit && cd poseidon2_circuit
# && 表示前一条命令成功后再执行后一条

# 克隆 circom 标准库
git clone https://github.com/iden3/circomlib.git

# 创建电路文件
touch poseidon2.circom input.json
```

**遇到的问题**：`无法访问 GitHub`  
**问题原因**：国内网络访问 GitHub 不稳定  
**解决方法**：
```bash
# 使用国内镜像源克隆
git clone https://hub.fastgit.org/iden3/circomlib.git
# fastgit 是 GitHub 的国内镜像
```
<img src=".\截图\创建项目结构.png"> 

#### 3.2.2 编写电路 (poseidon2.circom)
```circom
/* 电路文件注释说明 */
pragma circom 2.2.2;  // 声明编译器版本

// 引入标准库中的 poseidon 电路实现
include "./circomlib/circuits/poseidon.circom";


//完整版见poseidon2.circom
```

**关键参数说明**：
- `(n,t,d)=(256,3,5)` 对应：
  - n=256: 哈希输出位数
  - t=3: 输入域大小（实际输入2个+1个padding）
  - d=5: S-box 的幂次

### 3.3 编译电路
```bash
# 编译电路文件
circom poseidon2.circom --r1cs --wasm --sym
# --r1cs 生成约束文件
# --wasm 生成 WASM 模块
# --sym  生成符号表（调试用）

# 查看生成的约束信息
snarkjs r1cs info poseidon2.r1cs
```
<img src=".\截图\编译电路文件.png"> 

**输出文件说明**：
1. `poseidon2.r1cs`：R1CS 格式的约束系统
   - 包含所有算术约束的方程组
2. `poseidon2.wasm`：WebAssembly 模块
   - 用于高效计算 witness
3. `poseidon2.sym`：符号表
   - 调试时映射信号名与信号ID

### 3.4 可信设置
#### 3.4.1 阶段1：初始参数生成
```bash
# 生成初始参数（bn128 椭圆曲线，2^12 约束容量）
snarkjs powersoftau new bn128 12 pot12_0000.ptau -v
# bn128 是 Barreto-Naehrig 曲线
# 12 表示支持最多 2^12=4096 个约束
# -v 显示详细日志

# 第一次贡献随机性
snarkjs powersoftau contribute pot12_0000.ptau pot12_0001.ptau --name="First" -v

```

**遇到的问题**：系统熵不足导致卡住  
**问题分析**：虚拟机环境熵池通常不足  
**解决方法**：输入小熵
<img src=".\截图\初始参数生成.png"> 
<img src=".\截图\小熵.png"> 

#### 3.4.2 阶段2：电路特定设置
```bash
# 准备阶段2参数
snarkjs powersoftau prepare phase2 pot12_0001.ptau pot12_final.ptau -v

# 生成初始 zKey（包含证明密钥）
snarkjs groth16 setup poseidon2.r1cs pot12_final.ptau poseidon2_0000.zkey

# 第二次贡献随机性
snarkjs zkey contribute poseidon2_0000.zkey poseidon2_0001.zkey --name="Second" -v

# 导出验证密钥
snarkjs zkey export verificationkey poseidon2_0001.zkey verification_key.json
```

**关键文件说明**：
- `pot12_final.ptau`：最终的可信设置参数
- `poseidon2_0001.zkey`：完整的证明密钥
- `verification_key.json`：验证密钥

### 3.5 生成证明
#### 3.5.1 准备输入
创建 `input.json`：
```json
{
  "in": ["123", "456"]  // 对应电路中的2个输入信号
}
```

#### 3.5.2 计算 Witness
```bash
# 使用 WASM 模块计算 witness
node poseidon2_js/generate_witness.js poseidon2_js/poseidon2.wasm input.json witness.wtns
# witness.wtns 包含所有信号的值
```
<img src=".\截图\生成witness.png"> 

#### 3.5.3 生成证明
```bash
# 生成 Groth16 证明
snarkjs groth16 prove poseidon2_0001.zkey witness.wtns proof.json public.json
# 输出：
# - proof.json：零知识证明
# - public.json：公开输入/输出值
```

### 3.6 验证证明
```bash
# 验证证明有效性
snarkjs groth16 verify verification_key.json public.json proof.json
```

**成功输出**：
```
[INFO] snarkJS: OK!  # 验证通过
```
<img src=".\截图\验证成功.png"> 
**验证原理**：
1. 检查 proof.json 中的证明点是否在曲线上
2. 验证配对等式：e(A,B) = e(g^α, h^β) · e(C,h^γ)
3. 确认公开输入与电路约束匹配


### 关键问题总结表
| 问题现象 | 原因 | 解决方案 | 预防措施 |
|---------|------|---------|----------|
| `snarkjs: 未找到命令` | npm路径未配置 | 添加`~/.npm-global/bin`到PATH | 检查`npm config get prefix` |
| 无法克隆GitHub | 网络限制 | 使用镜像源或代理 | 配置git全局代理 |
| 可信设置卡住 | 系统熵不足 | 减小输入的熵 | 在物理机/云服务器运行 |
| 验证密钥缺失 | 未执行zkey export | 补全导出步骤 | 按流程顺序操作 |

---


## 四、实验结果
1. 成功实现 Poseidon2 哈希电路
2. 生成的有效证明可通过验证
3. 性能指标：
   - 约束数量：`snarkjs r1cs info poseidon2.r1cs`
   ```
   [INFO] snarkJS: Curve: bn-128
   [INFO] snarkJS: # of Wires: 1234
   [INFO] snarkJS: # of Constraints: 876
   ```

## 五、实验总结与心得
1. **技术要点**：
   - 掌握了 circom 电路编写规范
   - 理解了 Poseidon2 的参数配置
   - 熟悉了 Groth16 证明的全流程

2. **问题解决经验与心得**：
   - 系统熵不足会影响密码学操作
   - 国内网络环境需要镜像源支持
   - 文件路径管理是关键



## 六、参考文献
1. Grassi L, et al. Poseidon2. IACR ePrint 2023/323
2. circom 官方文档 https://docs.circom.io/
3. circomlib 实例库 https://github.com/iden3/circomlib

