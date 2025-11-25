# Minecraft 资源包合并器

一个简单易用的工具，用于合并多个Minecraft资源包。支持Web界面和命令行两种方式。

## ✨ 特性

- 🌐 **Web界面** - 拖拽上传，可视化调整优先级
- 🎨 **自定义图标** - 上传任意图片作为资源包封面，自动处理为 128x128 PNG
- 🔧 **智能合并** - 自动合并JSON文件（语言、音效、字体、标签等）
- 📦 **通用支持** - 自动检测任意资源包，只需包含 `pack.mcmeta`

## 🚀 快速开始

### Web界面（推荐）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动应用
python app.py

# 3. 打开浏览器访问 http://localhost:5000
```

**使用步骤：**
1. 上传 .zip 资源包文件
2. 拖动卡片调整优先级（下方=高优先级）
3. （可选）上传自定义图标 - 系统会自动处理为 128x128 方形 PNG
4. 点击"开始合并"
5. 下载合并后的资源包

### 命令行

```bash
# 自动检测并合并当前目录所有资源包
python merge_packs.py --output merged_pack --clean --summary --zip

# 指定资源包和优先级（从低到高）
python merge_packs.py \
    --packs "基础包" "增强包" "自定义包" \
    --output my_pack \
    --clean --summary --zip
```

## 📖 合并规则

| 文件类型 | 合并方式 |
|---------|---------|
| 语言文件 (`lang/*.json`) | 键值合并，后者覆盖前者 |
| 音效配置 (`sounds.json`) | 字典合并 |
| 字体配置 (`font/*.json`) | 数组合并去重 |
| 图集配置 (`atlases/*.json`) | 数组合并去重 |
| 数据标签 (`tags/*.json`) | 值数组合并去重 |
| 其他文件 | 后来者覆盖 |
| `pack.png` | 取最高优先级包 |
| `pack.mcmeta` | 自动生成 (format取最大值) |

**重要：** 优先级顺序决定覆盖规则，越靠后的包优先级越高。

## 🎨 自定义图标功能

通过 Web 界面，您可以上传自定义图片作为合并后资源包的封面图标。

**支持的图片格式：**
- PNG, JPG/JPEG, GIF, BMP, WEBP

**自动处理：**
- ✅ 自动裁剪为正方形（从中心裁剪）
- ✅ 自动缩放到 128x128 像素
- ✅ 自动转换为 PNG 格式
- ✅ 使用高质量 LANCZOS 重采样
- ✅ 支持透明背景

**使用建议：**
- 推荐使用正方形图片（避免裁剪）
- 建议分辨率至少 128x128 或更高
- 支持透明背景的 PNG 效果最佳

详细说明请参考 [CUSTOM_ICON_FEATURE.md](CUSTOM_ICON_FEATURE.md)

## 🔍 命令行参数

```bash
--packs [包1] [包2] ...    # 指定资源包（低→高优先级）
--output 名称              # 输出目录名（默认: merged_pack）
--clean                    # 合并前清空输出目录
--summary                  # 显示统计信息
--zip                      # 创建zip压缩包
--pack-format 版本         # 覆盖pack_format
--description "描述"       # 自定义描述
--dry-run                  # 预览不执行
```

## 💡 使用示例

**合并多个资源包：**
```bash
python merge_packs.py \
    --packs "pack_base" "pack_addon" "pack_custom" \
    --output merged_output \
    --description "我的合并资源包" \
    --zip
```

**预览合并效果：**
```bash
python merge_packs.py --dry-run --summary
```

## 🐛 常见问题

**Q: 找不到资源包？**  
A: 确保资源包包含 `pack.mcmeta` 文件，或使用 `--packs` 参数指定路径。

**Q: Web应用无法访问？**  
A: 检查5000端口是否被占用，确保已安装Flask: `pip install -r requirements.txt`

**Q: 如何设置优先级？**  
A: 在列表/参数中越靠后的包优先级越高。例如：基础包→额外包→自定义包

**Q: 支持哪些版本？**  
A: 支持所有使用 `pack.mcmeta` 格式的Minecraft版本（1.6.1+）

## 📝 注意事项

- 上传限制为500MB
- Web界面临时文件24小时后自动清理
- 建议合并前备份重要资源包
- 使用 `--dry-run` 可预览合并效果

---

**获取帮助：** `python merge_packs.py --help`

