import typer
import subprocess
import sys

app = typer.Typer(help="Polycarb 智能体管理工具")

@app.command()
def doctor():
    """[智能体] 运行数据医生，进行全量数据体检"""
    subprocess.run([sys.executable, "scripts/agent_tools/data_doctor.py"])

@app.command()
def test():
    """[智能体] 运行 Pytest 测试套件"""
    print("🚀 正在运行自动化测试...")
    result = subprocess.run(["pytest", "tests/"], capture_output=False)
    if result.returncode != 0:
        print("\n❌ 测试失败！请将报错信息发给 Trae 进行修复。")
    else:
        print("\n✅ 所有测试通过，系统逻辑稳健。")

if __name__ == "__main__":
    app()