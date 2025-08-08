import cv2
import numpy as np
import matplotlib.pyplot as plt
import skimage.util as skiu
from skimage import transform, metrics

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置中文字体为黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 数字水印嵌入类
class DCT_Embed(object):
    def __init__(self, background, watermark, block_size=8, alpha=30):
        # 验证背景图像和水印图像尺寸关系
        b_h, b_w = background.shape[:2]
        w_h, w_w = watermark.shape[:2]
        assert w_h <= b_h / block_size and w_w <= b_w / block_size, f"水印图像尺寸必须不大于背景图像尺寸的1/{block_size}"

        # 保存参数
        self.block_size = block_size
        self.alpha = alpha  # 水印强度控制
        self.k1 = np.random.randn(block_size)  # 随机序列1
        self.k2 = np.random.randn(block_size)  # 随机序列2

    # DCT分块处理
    def dct_blkproc(self, background):
        # 计算分块后的行数和列数
        h_blocks = background.shape[0] // self.block_size
        w_blocks = background.shape[1] // self.block_size

        # 初始化DCT块存储数组
        dct_blocks = np.zeros(shape=(h_blocks, w_blocks, self.block_size, self.block_size))

        # 垂直分割图像
        v_blocks = np.vsplit(background, h_blocks)

        # 对每个垂直块进行水平分割并计算DCT
        for i in range(h_blocks):
            h_blocks = np.hsplit(v_blocks[i], w_blocks)
            for j in range(w_blocks):
                dct_blocks[i, j, ...] = cv2.dct(h_blocks[j].astype(np.float64))

        return dct_blocks

    # 嵌入水印
    def embed_watermark(self, dct_data, watermark):
        # 验证水印是否为二值化
        assert watermark.max() == 1 and watermark.min() == 0, "水印必须为二值化处理后的图像"

        # 创建嵌入水印后的DCT块副本
        embedded_data = dct_data.copy()

        # 在每个DCT块的最后一列嵌入水印
        for i in range(watermark.shape[0]):
            for j in range(watermark.shape[1]):
                # 根据水印值选择随机序列
                k = self.k1 if watermark[i, j] == 1 else self.k2
                for k_index in range(self.block_size):
                    embedded_data[i, j, k_index, self.block_size - 1] += self.alpha * k[k_index]

        return embedded_data

    # 逆DCT变换重建图像
    def reconstruct_image(self, dct_data):
        rows, cols = dct_data.shape[0], dct_data.shape[1]
        result = None

        # 逐行重建图像
        for i in range(rows):
            row = None
            for j in range(cols):
                # 对每个DCT块进行逆DCT变换
                block = cv2.idct(dct_data[i, j, ...])
                row = block if j == 0 else np.hstack((row, block))  # 水平拼接
            result = row if i == 0 else np.vstack((result, row))  # 垂直拼接

        return result.astype(np.uint8)

    # 提取水印
    def extract_watermark(self, image, watermark_size):
        # 获取水印大小
        w_h, w_w = watermark_size

        # 创建初始水印
        recovered_watermark = np.zeros(shape=watermark_size)

        # 对图像进行DCT分块处理
        dct_blocks = self.dct_blkproc(image)

        # 对每个DCT块进行处理
        p = np.zeros(self.block_size)
        for i in range(w_h):
            for j in range(w_w):
                # 获取DCT块的最后一列
                for k in range(self.block_size):
                    p[k] = dct_blocks[i, j, k, self.block_size - 1]

                # 计算与随机序列的相关性
                try:
                    if corr2(p, self.k1) > corr2(p, self.k2):
                        recovered_watermark[i, j] = 1
                    else:
                        recovered_watermark[i, j] = 0
                except:
                    recovered_watermark[i, j] = 0

        return recovered_watermark


# 攻击类
class Attack(object):
    @staticmethod
    def add_gaussian_noise(image, mean=0.0, var=1e-2):
        """添加高斯噪声"""
        return (skiu.random_noise(image, mode="gaussian", mean=mean, var=var) * 255).astype(np.uint8)

    @staticmethod
    def add_salt_pepper(image):
        """添加椒盐噪声"""
        return (skiu.random_noise(image, mode="s&p") * 255).astype(np.uint8)

    @staticmethod
    def rotate_image(image, angle=45):
        """旋转图像"""
        return transform.rotate(image, angle, preserve_range=True).astype(np.uint8)

    @staticmethod
    def flip_image(image, flip_code=1):
        """翻转图像"""
        return cv2.flip(image, flip_code)

    @staticmethod
    def translate_image(image, x, y):
        """平移图像"""
        rows, cols = image.shape[:2]
        M = np.float32([[1, 0, x], [0, 1, y]])
        return cv2.warpAffine(image, M, (cols, rows))

    @staticmethod
    def crop_image(image, x_start, x_end, y_start, y_end):
        """裁剪图像"""
        return image[y_start:y_end, x_start:x_end]

    @staticmethod
    def adjust_brightness(image, value):
        """调整亮度"""
        return cv2.convertScaleAbs(image, alpha=1, beta=value)

    @staticmethod
    def adjust_contrast(image, value):
        """调整对比度"""
        return cv2.addWeighted(image, value, np.zeros_like(image), 0, 0)


# 计算相关性
def corr2(a, b):
    # 计算均值
    a_mean = np.mean(a)
    b_mean = np.mean(b)

    # 去均值处理
    a_centered = a - a_mean
    b_centered = b - b_mean

    # 计算分母
    denom = np.sqrt(np.sum(a_centered ** 2) * np.sum(b_centered ** 2))

    # 防止除零
    if denom == 0:
        return 0

    # 计算相关系数
    r = np.sum(a_centered * b_centered) / denom
    return r


# 主函数
if __name__ == '__main__':
    # 参数设置
    alpha = 10
    block_size = 8

    # 加载水印
    watermark = cv2.imread(r"sduqingdao_logo.bmp")
    watermark = cv2.cvtColor(watermark, cv2.COLOR_BGR2RGB)
    watermark_bin = np.where(watermark < np.mean(watermark, axis=(0, 1)), 0, 1)

    # 加载背景图像
    background = cv2.imread(r"sduqingdao_background.bmp")
    background = cv2.cvtColor(background, cv2.COLOR_BGR2RGB)
    background_backup = background.copy()

    # 调整背景图像尺寸为块大小的倍数
    h, w = background.shape[:2]
    if h % block_size != 0:
        h -= h % block_size
    if w % block_size != 0:
        w -= w % block_size
    background = background[:h, :w, :]

    # 按通道处理背景图像
    channels = cv2.split(background)
    embedded_images = []
    extracted_watermarks = []
    embed_objects = []

    # 对每个颜色通道进行处理
    for i in range(3):
        embed = DCT_Embed(background=channels[i], watermark=watermark_bin[..., i], block_size=block_size, alpha=alpha)

        # DCT分块处理
        dct_blocks = embed.dct_blkproc(channels[i])

        # 嵌入水印
        embedded_blocks = embed.embed_watermark(dct_blocks, watermark_bin[..., i])

        # 重建图像
        embedded_image = embed.reconstruct_image(embedded_blocks)
        embedded_images.append(embedded_image)

        # 提取水印
        extracted_watermark = embed.extract_watermark(embedded_image, watermark_bin[..., i].shape) * 255
        extracted_watermarks.append(extracted_watermark)

        # 保存嵌入对象
        embed_objects.append(embed)

    # 合并通道
    merged_image = cv2.merge(embedded_images)
    merged_watermark = cv2.merge([ew.astype(np.uint8) for ew in extracted_watermarks])

    # 显示原始图像及相关结果
    plt.figure(figsize=(12, 8))
    images = [background_backup, watermark, merged_image, merged_watermark]
    titles = ["原始图像", "水印", "嵌入水印后的图像", "提取的水印"]

    for i in range(4):
        plt.subplot(2, 2, i + 1)
        plt.imshow(images[i])
        plt.title(titles[i])
        plt.axis("off")

    plt.tight_layout()
    plt.savefig('嵌入与提取.png', dpi=300, bbox_inches='tight')
    plt.show()

    # 定义攻击列表
    attacks = [
        ("高斯噪声", lambda img: Attack.add_gaussian_noise(img, var=0.01)),
        ("椒盐噪声", Attack.add_salt_pepper),
        ("旋转", lambda img: Attack.rotate_image(img, angle=30)),
        ("水平翻转", lambda img: Attack.flip_image(img, flip_code=1)),
        ("垂直翻转", lambda img: Attack.flip_image(img, flip_code=0)),
        ("平移", lambda img: Attack.translate_image(img, 20, 20)),
        ("裁剪", lambda img: Attack.crop_image(img, 50, 100, 50, 100)),
        ("亮度调整", lambda img: Attack.adjust_brightness(img, 20)),
        ("对比度调整", lambda img: Attack.adjust_contrast(img, 1.5))
    ]

    # 图像展示布局
    plt.figure(figsize=(18, 8))

    # 原始水印图像
    plt.subplot(2, len(attacks) + 1, 1)
    plt.imshow(merged_image)
    plt.title("未受攻击的水印图像")
    plt.axis('off')

    plt.subplot(2, len(attacks) + 1, len(attacks) + 2)
    plt.imshow(merged_watermark)
    plt.title("未受攻击的提取水印")
    plt.axis('off')

    # 对每个攻击类型进行处理
    for idx, (attack_name, attack_func) in enumerate(attacks):
        attacked_image = attack_func(merged_image.copy())

        # 分离通道
        attacked_channels = cv2.split(attacked_image)
        attacked_watermarks = []

        # 提取水印
        for i in range(3):
            try:
                extracted = embed_objects[i].extract_watermark(attacked_channels[i], watermark_bin[..., i].shape) * 255
                attacked_watermarks.append(extracted)
            except:
                attacked_watermarks.append(np.zeros(watermark_bin[..., i].shape))

        # 合并水印
        attacked_merged_watermark = cv2.merge([ew.astype(np.uint8) for ew in attacked_watermarks])

        # 计算PSNR
        try:
            psnr = metrics.peak_signal_noise_ratio(merged_image, attacked_image, data_range=255)
        except:
            psnr = float('inf')

        # 显示攻击后的图像和水印
        plt.subplot(2, len(attacks) + 1, idx + 2)
        plt.imshow(attacked_image)
        plt.title(f"{attack_name}\nPSNR: {psnr:.2f}dB")
        plt.axis('off')

        plt.subplot(2, len(attacks) + 1, len(attacks) + 3 + idx)
        plt.imshow(attacked_merged_watermark)
        plt.title(f"{attack_name}后的提取水印")
        plt.axis('off')

    plt.tight_layout()
    plt.savefig('鲁棒性测试.png', dpi=300, bbox_inches='tight')
    plt.show()