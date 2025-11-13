#!/usr/bin/env python3
"""
快速演示脚本 - 展示如何使用资源包合并器
"""
import subprocess
import sys
from pathlib import Path

def print_header(text):
    """打印美化的标题"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def run_command(cmd, description):
    """运行命令并显示结果"""
    print(f"🔸 {description}")
    print(f"   命令: {cmd}")
    print()
    result = subprocess.run(cmd, shell=True, capture_output=False)
    return result.returncode == 0

def main():
    print_header("Minecraft 资源包合并器 - 快速演示")

    print("本脚本将演示如何使用资源包合并器的各种功能。\n")

    # 检查系统
    print_header("步骤 1: 系统检查")
    if not run_command("python test_system.py", "运行系统测试"):
        print("❌ 系统测试失败，请检查配置")
        return 1

    # 命令行示例
    print_header("步骤 2: 命令行合并示例")

    print("📝 示例 1: 查看帮助信息")
    run_command("python merge_packs.py --help | head -20", "显示命令行帮助")

    print("\n📝 示例 2: 模拟合并（不实际写入）")
    run_command(
        "python merge_packs.py --output demo_merge --dry-run --summary | head -30",
        "Dry-run模式查看合并计划"
    )

    print("\n📝 示例 3: 实际合并资源包")
    cmd = "python merge_packs.py --output demo_merged --clean --summary"
    print(f"💡 你可以运行以下命令实际合并资源包：")
    print(f"   {cmd}")

    # Web应用说明
    print_header("步骤 3: Web应用使用")

    print("🌐 启动Web应用:")
    print("   方式1: ./start.sh")
    print("   方式2: python app.py")
    print()
    print("📱 然后在浏览器访问: http://localhost:5000")
    print()
    print("✨ Web界面特性:")
    print("   • 拖拽上传 .zip 资源包文件")
    print("   • 可视化调整优先级（拖动卡片）")
    print("   • 配置输出选项")
    print("   • 一键下载合并结果")

    # 使用技巧
    print_header("使用技巧")

    tips = [
        ("优先级设置", "基础包在前（低优先级），覆盖包在后（高优先级）"),
        ("预览效果", "使用 --dry-run 参数可以预览合并，不实际写入文件"),
        ("自动检测", "不指定 --packs 参数会自动检测所有有效资源包"),
        ("压缩输出", "添加 --zip 参数会自动创建 .zip 压缩包"),
        ("自定义格式", "使用 --pack-format 和 --description 自定义元数据"),
    ]

    for i, (title, tip) in enumerate(tips, 1):
        print(f"{i}. {title}")
        print(f"   {tip}\n")

    # 完成
    print_header("演示完成")

    print("✅ 所有功能演示完毕！\n")
    print("📚 更多信息请查看:")
    print("   • README.md - 项目概览")
    print("   • README_WEB.md - 详细文档")
    print("   • QUICKSTART.md - 快速开始指南")
    print()
    print("🚀 现在你可以:")
    print("   1. 运行 'python app.py' 启动Web应用")
    print("   2. 或使用命令行: 'python merge_packs.py --help'")
    print()

    return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  演示已取消")
        sys.exit(0)

