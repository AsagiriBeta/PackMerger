#!/usr/bin/env python3
"""
测试脚本 - 验证资源包合并功能
"""
from pathlib import Path
import sys

def test_imports():
    """测试所有必要的导入"""
    print("🧪 测试导入...")
    try:
        import flask
        print("  ✅ Flask")
        import werkzeug
        print("  ✅ Werkzeug")
        from merge_packs import (
            is_valid_resource_pack,
            detect_packs,
            load_pack_info,
            Merger
        )
        print("  ✅ merge_packs 模块")
        return True
    except ImportError as e:
        print(f"  ❌ 导入失败: {e}")
        return False

def test_detect_packs():
    """测试资源包检测"""
    print("\n🧪 测试资源包检测...")
    from merge_packs import detect_packs, is_valid_resource_pack

    cwd = Path.cwd()

    # 手动检查已知的包
    known_packs = [
        "guns++-5.8.4",
        "Gamingbarn's Guns - Resources V1",
        "Armor",
        "NOTLIVES's SWAT Shield 1"
    ]

    found = []
    for pack_name in known_packs:
        pack_path = cwd / pack_name
        if pack_path.exists() and is_valid_resource_pack(pack_path):
            found.append(pack_name)
            print(f"  ✅ 找到: {pack_name}")
        else:
            print(f"  ℹ️  未找到: {pack_name}")

    if found:
        print(f"\n  总计找到 {len(found)} 个有效资源包")
        return True
    else:
        print("\n  ⚠️  未找到资源包（这是正常的，如果你还没上传包的话）")
        return True

def test_file_structure():
    """测试文件结构"""
    print("\n🧪 测试文件结构...")
    required_files = [
        "merge_packs.py",
        "app.py",
        "requirements.txt",
        "templates/index.html",
        "README_WEB.md",
        "QUICKSTART.md"
    ]

    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} 不存在")
            all_exist = False

    return all_exist

def test_directories():
    """测试必要的目录"""
    print("\n🧪 测试目录结构...")
    required_dirs = ["templates", "uploads", "outputs"]

    all_exist = True
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists() and dir_path.is_dir():
            print(f"  ✅ {dir_name}/")
        else:
            print(f"  ⚠️  {dir_name}/ 不存在，正在创建...")
            dir_path.mkdir(exist_ok=True)
            print(f"  ✅ {dir_name}/ 已创建")

    return True

def test_flask_app():
    """测试Flask应用配置"""
    print("\n🧪 测试Flask应用配置...")
    try:
        from app import app
        print(f"  ✅ Flask应用已加载")
        print(f"  ✅ 上传文件夹: {app.config['UPLOAD_FOLDER']}")
        print(f"  ✅ 输出文件夹: {app.config['OUTPUT_FOLDER']}")
        print(f"  ✅ 最大上传大小: {app.config['MAX_CONTENT_LENGTH'] / (1024*1024):.0f}MB")
        return True
    except Exception as e:
        print(f"  ❌ Flask应用加载失败: {e}")
        return False

def main():
    print("=" * 60)
    print("Minecraft 资源包合并器 - 系统测试")
    print("=" * 60)

    results = []

    results.append(("导入测试", test_imports()))
    results.append(("文件结构测试", test_file_structure()))
    results.append(("目录结构测试", test_directories()))
    results.append(("Flask应用测试", test_flask_app()))
    results.append(("资源包检测测试", test_detect_packs()))

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    all_passed = True
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
        if not result:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 所有测试通过！系统已就绪。")
        print("\n下一步:")
        print("  1. 启动Web应用: ./start.sh 或 python app.py")
        print("  2. 访问: http://localhost:5000")
        print("  3. 或使用命令行: python merge_packs.py --help")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查错误信息。")
        return 1

if __name__ == '__main__':
    sys.exit(main())

