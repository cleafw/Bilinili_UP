"""
B站UP主筛选工具 - 主程序入口
"""
import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    """主程序入口"""
    app = QApplication(sys.argv)
    app.setApplicationName("B站UP主筛选工具")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
