#!/bin/bash
# ============================================
# WeasyPrint Linux 安装脚本
# 用于解决 PDF 中文乱码和样式问题
# 支持 Ubuntu/Debian 和 CentOS/RHEL
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "============================================"
echo " WeasyPrint Linux 安装脚本"
echo " 用于解决 PDF 中文乱码和样式问题"
echo "============================================"
echo ""

# 检查是否在虚拟环境中
if [ -n "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}[信息] 检测到虚拟环境: $VIRTUAL_ENV${NC}"
    echo "  weasyprint 将安装到该虚拟环境中（仅当前项目可用）"
    echo ""
    PIP_CMD="pip"
else
    echo -e "${YELLOW}[警告] 未检测到虚拟环境！${NC}"
    echo ""
    echo "  weasyprint 将安装到全局 Python，可能影响其他项目。"
    echo "  建议先激活项目虚拟环境再运行此脚本："
    echo ""
    echo "    cd $(dirname "$0")"
    echo "    source .venv/bin/activate"
    echo "    ./install_weasyprint_linux.sh"
    echo ""
    read -p "是否继续安装到全局 Python？(y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
    PIP_CMD="pip3"
fi

# 检查 root 权限（系统依赖需要 root）
check_root() {
    if [ "$EUID" -ne 0 ]; then
        SUDO="sudo"
    else
        SUDO=""
    fi
}

# 检测 Linux 发行版
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    elif command -v lsb_release &> /dev/null; then
        DISTRO=$(lsb_release -is | tr '[:upper:]' '[:lower:]')
    else
        DISTRO="unknown"
    fi
    echo -e "[信息] 检测到发行版: ${DISTRO}"
}

# 安装系统依赖 - Debian/Ubuntu
install_deps_debian() {
    echo ""
    echo "[步骤 1/3] 安装系统依赖 (Debian/Ubuntu)..."
    $SUDO apt-get update -qq
    $SUDO apt-get install -y -qq \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libffi-dev \
        shared-mime-info \
        fonts-noto-cjk \
        2>/dev/null || true
    echo "  系统依赖安装完成"
}

# 安装系统依赖 - CentOS/RHEL
install_deps_rhel() {
    echo ""
    echo "[步骤 1/3] 安装系统依赖 (CentOS/RHEL)..."
    $SUDO yum install -y \
        pango \
        gdk-pixbuf2 \
        libffi-devel \
        shared-mime-info \
        google-noto-sans-cjk-ttc-fonts \
        2>/dev/null || $SUDO dnf install -y \
        pango \
        gdk-pixbuf2 \
        libffi-devel \
        shared-mime-info \
        google-noto-sans-cjk-ttc-fonts
    echo "  系统依赖安装完成"
}

# 安装系统依赖 - Alpine
install_deps_alpine() {
    echo ""
    echo "[步骤 1/3] 安装系统依赖 (Alpine)..."
    $SUDO apk add --no-cache \
        pango \
        gdk-pixbuf \
        libffi-dev \
        shared-mime-info \
        font-noto-cjk
    echo "  系统依赖安装完成"
}

# 安装 weasyprint
install_weasyprint() {
    echo ""
    echo "[步骤 2/3] 安装 weasyprint (Python 包)..."
    $PIP_CMD install "weasyprint>=61.0"
    echo "  weasyprint 安装完成"
}

# 验证安装
verify_installation() {
    echo ""
    echo "[步骤 3/3] 验证安装..."

    PYTHON="python3"
    command -v python3 &> /dev/null || PYTHON="python"

    # 验证导入
    $PYTHON -c "from weasyprint import HTML; print('  weasyprint 导入成功')" 2>/dev/null || {
        echo -e "${RED}  [错误] weasyprint 导入失败${NC}"
        exit 1
    }

    # 验证版本
    $PYTHON -c "import weasyprint; print(f'  版本: {weasyprint.__version__}')"

    # 验证中文渲染
    $PYTHON -c "from weasyprint import HTML; HTML(string='<html><body><p>中文测试</p></body></html>').write_pdf(); print('  中文字体渲染正常')" 2>/dev/null || {
        echo -e "${YELLOW}  [警告] PDF 生成测试失败，可能需要安装中文字体${NC}"
        echo "  安装字体: sudo apt-get install fonts-noto-cjk"
    }
}

# 主流程
check_root
detect_distro

case $DISTRO in
    ubuntu|debian|linuxmint|pop)
        install_deps_debian
        ;;
    centos|rhel|fedora|rocky|alma)
        install_deps_rhel
        ;;
    alpine)
        install_deps_alpine
        ;;
    *)
        echo -e "${YELLOW}[警告] 未识别的发行版: $DISTRO${NC}"
        echo "请手动安装以下系统依赖："
        echo "  - pango / libpango"
        echo "  - gdk-pixbuf / libgdk-pixbuf"
        echo "  - libffi-dev / libffi-devel"
        echo "  - shared-mime-info"
        echo "  - 中文字体 (Noto Sans CJK 或 WenQuanYi)"
        echo ""
        read -p "是否继续安装 weasyprint Python 包？(y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        ;;
esac

install_weasyprint
verify_installation

echo ""
echo "============================================"
echo -e " ${GREEN}安装完成！PDF 渲染将使用 weasyprint 引擎${NC}"
echo "============================================"
