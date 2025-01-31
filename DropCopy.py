import sys
import os
import shutil
import random
import string
import time
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


def generate_suffix():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))


class FileDropArea(QGroupBox):
    filesDropped = pyqtSignal(list)

    def __init__(self, title):
        super().__init__(title)
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QGroupBox {
                border: 2px dashed #aaa;
                border-radius: 5px;
                margin-top: 1ex;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
        """)
        self.setMinimumSize(400, 150)

        layout = QVBoxLayout()
        self.label = QLabel("拖放文件到这里")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.setLayout(layout)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        files = [url.toLocalFile() for url in urls if os.path.isfile(url.toLocalFile())]
        if files:
            self.filesDropped.emit(files)
            # 更新显示的文件数量
            total_files = len(files) + int(self.label.text().split(" ")[-2]) if "已选择" in self.label.text() else len(files)
            self.label.setText(f"已选择 {total_files} 个文件")
        else:
            QMessageBox.warning(self, "警告", "拖放的文件无效，请检查！")
        event.acceptProposedAction()


# 自定义信号类
class WorkerSignals(QObject):
    progress_signal = pyqtSignal()
    error_signal = pyqtSignal(str)


class CopyWorker(QRunnable):
    def __init__(self, src, dst):
        super().__init__()
        self.src = src
        self.dst = dst
        self.signals = WorkerSignals()

    def run(self):
        try:
            if os.path.exists(self.dst):
                base, ext = os.path.splitext(self.dst)
                new_dst = f"{base}_{generate_suffix()}{ext}"
                shutil.copy2(self.src, new_dst)
            else:
                shutil.copy2(self.src, self.dst)
        except Exception as e:
            self.signals.error_signal.emit(f"Error copying {self.src}: {str(e)}")
        finally:
            self.signals.progress_signal.emit()


class DropZoneWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.files = []
        layout = QVBoxLayout()

        self.drop_area = FileDropArea("拖放区域")
        self.drop_area.filesDropped.connect(self.handle_files_dropped)

        self.output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.select_output_path)
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self.delete_self)

        self.output_layout.addWidget(self.output_path)
        self.output_layout.addWidget(self.browse_btn)
        self.output_layout.addWidget(self.delete_btn)

        layout.addWidget(self.drop_area)
        layout.addLayout(self.output_layout)
        self.setLayout(layout)

    def handle_files_dropped(self, files):
        # 只添加不存在于已有列表中的文件
        new_files = [file for file in files if file not in self.files]
        self.files.extend(new_files)
        # 更新显示的文件数量
        total_files = len(self.files)
        self.drop_area.label.setText(f"已选择 {total_files} 个文件")

    def select_output_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path and os.path.isdir(path):
            self.output_path.setText(path)
        else:
            QMessageBox.warning(self, "警告", "选择的目录无效，请重新选择！")

    def delete_self(self):
        self.setParent(None)
        self.deleteLater()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件复制中转站")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("""
            QPushButton {
                padding: 5px 10px;
                font-size: 12px;
            }
            QLineEdit {
                padding: 5px;
                font-size: 12px;
            }
            QProgressBar {
                font-size: 12px;
            }
        """)

        # 加载图标文件
        icon_path = "app.ico"  # 替换为你的图标文件路径
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            self.setWindowIcon(icon)

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        self.layout = QVBoxLayout()
        self.drop_zones = []

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% (%v/%m)")
        self.progress_bar.show()

        self.add_zone_btn = QPushButton("添加拖入区域")
        self.add_zone_btn.clicked.connect(self.add_drop_zone)

        self.copy_btn = QPushButton("开始复制")
        self.copy_btn.clicked.connect(self.start_copy)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.add_zone_btn)
        button_layout.addWidget(self.copy_btn)

        self.layout.addLayout(button_layout)
        self.layout.addWidget(self.progress_bar)
        self.main_widget.setLayout(self.layout)

        self.thread_pool = QThreadPool.globalInstance()
        self.total_files = 0
        self.completed_files = 0
        self.start_time = 0
        self.add_drop_zone()

    def add_drop_zone(self):
        drop_zone = DropZoneWidget()
        self.drop_zones.append(drop_zone)
        self.layout.insertWidget(len(self.drop_zones) + 1, drop_zone)

    def start_copy(self):
        # 计算总文件数
        self.total_files = sum(
            len(zone.files)
            for zone in self.drop_zones
            if zone.output_path.text() and zone.files
        )

        if self.total_files == 0:
            QMessageBox.warning(self, "警告", "没有需要复制的文件！")
            return

        # 初始化进度条
        self.completed_files = 0
        self.progress_bar.setMaximum(self.total_files)
        self.progress_bar.setValue(0)
        self.start_time = time.time()

        # 禁用按钮
        self.copy_btn.setEnabled(False)
        self.add_zone_btn.setEnabled(False)

        # 开始复制
        for zone in self.drop_zones:
            output_path = zone.output_path.text()
            if not output_path or not zone.files:
                continue

            os.makedirs(output_path, exist_ok=True)

            for src in zone.files:
                if os.path.isfile(src):
                    dst = os.path.join(output_path, os.path.basename(src))
                    worker = CopyWorker(src, dst)
                    worker.signals.progress_signal.connect(self.update_progress)
                    worker.signals.error_signal.connect(self.show_error)
                    self.thread_pool.start(worker)

    def update_progress(self):
        self.completed_files += 1
        self.progress_bar.setValue(self.completed_files)

        elapsed_time = time.time() - self.start_time
        if self.completed_files > 0:
            remaining_time = (elapsed_time / self.completed_files) * (self.total_files - self.completed_files)
            self.progress_bar.setFormat(f"%p% (%v/%m) - 剩余时间: {int(remaining_time)}s")
        else:
            self.progress_bar.setFormat(f"%p% (%v/%m)")

        if self.completed_files == self.total_files:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.copy_btn.setEnabled(True)
            self.add_zone_btn.setEnabled(True)
            QMessageBox.information(self, "完成", "文件复制完成！")

            # 清空拖入区但保留路径
            for zone in self.drop_zones:
                zone.files = []
                zone.drop_area.label.setText("拖放文件到这里")

    def show_error(self, error_msg):
        QMessageBox.critical(self, "错误", error_msg)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())