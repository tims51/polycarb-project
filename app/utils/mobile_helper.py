
import socket
import qrcode
from io import BytesIO
import streamlit as st

def get_local_ip():
    """
    获取本机局域网IP地址
    使用UDP连接探测方式，不会实际发送数据
    """
    s = None
    try:
        # 创建一个UDP套接字
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 尝试连接到一个公共IP（此处使用Google DNS），不需要实际连接成功
        # 这会让系统决定使用哪个网络接口来路由
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        # 如果失败，回退到标准方法（可能返回127.0.0.1）
        ip = socket.gethostbyname(socket.gethostname())
    finally:
        if s:
            s.close()
    return ip

def generate_qr_code(data):
    """
    生成QR码图片
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    # 转换为字节流
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return img_byte_arr

def render_mobile_connect_sidebar():
    """
    在侧边栏渲染手机连接模块
    """
    with st.sidebar:
        st.markdown("---")
        st.subheader("📱 手机端访问")
        
        # 获取IP
        ip = get_local_ip()
        port = 8501 # 默认端口，如果不同需调整
        
        # 检查是否绑定了 0.0.0.0 (简单检查：如果是在localhost访问，可能没有开启远程)
        # 这里主要展示连接信息
        
        url = f"http://{ip}:{port}"
        
        # 生成二维码
        qr_img = generate_qr_code(url)
        
        st.image(qr_img, caption="扫码在手机打开", use_container_width=True)
        
        st.code(url, language="text")
        
        with st.expander("📝 连接说明"):
            st.markdown("""
            1. 确保手机和电脑连接**同一Wi-Fi**
            2. 使用手机相机或微信扫码
            3. 如果无法访问，请检查防火墙设置
            4. 必须使用 `run_mobile.bat` 启动
            """)
