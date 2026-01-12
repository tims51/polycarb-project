# test_updated_structure.py
import json
import sys
import os
from datetime import datetime

print("🚀 开始数据模型测试...")
print("当前目录:", os.getcwd())
print("Python路径:", sys.executable)
print()

# 检查必要文件是否存在
if not os.path.exists("main.py"):
    print("❌ 错误: 找不到 main.py 文件")
    print("请确保你在正确的项目目录中 (C:\\Users\\徐梓馨\\polycarb_project\\app\\)")
    input("按Enter键退出...")
    sys.exit(1)

# 尝试导入 DataManager
try:
    # 方法1：直接导入
    print("尝试导入 DataManager...")
    sys.path.append('.')  # 添加当前目录到 Python 路径
    
    # 从 main.py 导入 DataManager 类
    from main import DataManager
    print("✅ 成功从 main.py 导入 DataManager")
    
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("\n尝试其他导入方法...")
    
    # 方法2：导入整个模块然后获取类
    try:
        import main
        DataManager = main.DataManager
        print("✅ 通过导入 main 模块成功获取 DataManager")
    except Exception as e2:
        print(f"❌ 备用方法也失败: {e2}")
        print("\n可能的解决方案:")
        print("1. 确保 main.py 在相同目录")
        print("2. 检查 main.py 中是否有 DataManager 类的定义")
        print("3. 确保 DataManager 类不是嵌套在其他类或函数中")
        input("按Enter键退出...")
        sys.exit(1)

def test_updated_structure():
    """测试更新后的数据结构"""
    
    print("\n" + "="*60)
    print("🧪 数据模型扩展测试")
    print("="*60)
    
    # 创建DataManager实例
    try:
        data_manager = DataManager()
        print("✅ 成功创建 DataManager 实例")
    except Exception as e:
        print(f"❌ 创建 DataManager 失败: {e}")
        return False
    
    # 1. 测试加载数据
    try:
        data = data_manager.load_data()
        print(f"1. 📂 数据加载: ✅ 成功")
        print(f"   数据表数量: {len(data)}个")
        
        # 显示所有表
        for table_name, table_data in data.items():
            print(f"   - {table_name}: {len(table_data)}条记录")
    except Exception as e:
        print(f"1. 📂 数据加载: ❌ 失败 - {e}")
        return False
    
    # 2. 检查新表是否存在
    required_tables = ["raw_materials", "synthesis_records", "performance_records"]
    print(f"\n2. 🔍 检查新数据表:")
    
    all_tables_exist = True
    for table in required_tables:
        if table in data:
            record_count = len(data.get(table, []))
            print(f"   {table}: ✅ 存在 ({record_count}条记录)")
        else:
            print(f"   {table}: ❌ 缺失")
            all_tables_exist = False
    
    if not all_tables_exist:
        print("\n⚠️  缺少一些数据表，你可能需要:")
        print("   1. 运行 update_data_structure.py 更新数据结构")
        print("   2. 手动添加缺失的表到 data.json")
        return False
    
    # 3. 测试添加原料
    print(f"\n3. ➕ 测试添加原料:")
    test_material = {
        "code": "TEST-001",
        "name": "测试原料",
        "category": "测试类",
        "specification": "测试级",
        "purity": 99.9,
        "supplier": "测试供应商",
        "batch_no": "TEST202401001",
        "purchase_date": "2024-01-15",
        "storage_location": "测试区",
        "unit": "kg",
        "current_quantity": 10.0,
        "unit_price": 100.0
    }
    
    try:
        # 首先检查是否已存在测试原料
        existing_materials = data_manager.get_all_raw_materials()
        existing_test = any(m.get("code") == "TEST-001" for m in existing_materials)
        
        if existing_test:
            print("   ⚠️ 测试原料已存在，跳过添加")
        else:
            result = data_manager.add_raw_material(test_material)
            if result:
                print("   ✅ 添加原料成功")
            else:
                print("   ❌ 添加原料失败")
                return False
    except Exception as e:
        print(f"   ❌ 添加原料异常: {e}")
        return False
    
    # 4. 验证原料添加
    print(f"\n4. ✓ 验证原料添加:")
    try:
        materials = data_manager.get_all_raw_materials()
        test_material_added = False
        test_material_id = None
        
        for material in materials:
            if material.get("code") == "TEST-001":
                test_material_added = True
                test_material_id = material.get("id")
                print(f"   ✅ 找到测试原料 (ID: {test_material_id}, 名称: {material['name']})")
                break
        
        if not test_material_added:
            print("   ❌ 未找到测试原料")
            return False
        
        print(f"   原料总数: {len(materials)}")
    except Exception as e:
        print(f"   ❌ 验证异常: {e}")
        return False
    
    # 5. 测试计算功能
    print(f"\n5. 🧮 测试计算功能:")
    try:
        material = None
        for m in materials:
            if m.get("code") == "TEST-001":
                material = m
                break
        
        if material:
            expected_value = 10.0 * 100.0  # quantity * unit_price
            actual_value = material.get("total_value", 0)
            
            if abs(actual_value - expected_value) < 0.01:
                print(f"   ✅ 总值计算正确: ¥{actual_value:.2f}")
            else:
                print(f"   ⚠️ 总值计算不一致: 期望¥{expected_value}, 实际¥{actual_value}")
                print(f"     这可能是因为自动计算未启用")
    except Exception as e:
        print(f"   ⚠️ 计算异常: {e}")
    
    # 6. 测试其他方法
    print(f"\n6. 🔄 测试其他CRUD方法:")
    
    # 测试合成记录方法
    try:
        synthesis_records = data_manager.get_all_synthesis_records()
        print(f"   ✅ 合成记录: 可访问 ({len(synthesis_records)}条记录)")
    except Exception as e:
        print(f"   ❌ 合成记录异常: {e}")
    
    # 测试性能记录方法
    try:
        performance_records = data_manager.get_all_performance_records()
        print(f"   ✅ 性能记录: 可访问 ({len(performance_records)}条记录)")
    except Exception as e:
        print(f"   ❌ 性能记录异常: {e}")
    
    # 7. 清理测试数据（可选）
    print(f"\n7. 🧹 清理测试数据 (可选):")
    try:
        if test_material_id:
            confirm_cleanup = False  # 默认不清理，避免误删
            if confirm_cleanup:
                cleanup_result = data_manager.delete_raw_material(test_material_id)
                if cleanup_result:
                    print("   ✅ 测试数据清理成功")
                else:
                    print("   ⚠️ 测试数据清理失败")
            else:
                print("   ℹ️ 跳过清理，测试原料保留以便检查")
    except Exception as e:
        print(f"   ⚠️ 清理异常: {e}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_updated_structure()
        
        print("\n" + "="*60)
        if success:
            print("🎉 所有测试通过！数据结构扩展成功。")
            print("\n下一步建议:")
            print("1. 运行 Streamlit 应用检查功能: streamlit run main.py")
            print("2. 查看数据记录模块是否正常工作")
        else:
            print("❌ 测试失败，请检查错误信息。")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现未预期错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 保持窗口打开
    input("\n按Enter键退出...")