import sys
import os
import shutil
import random
import string
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
        files = [url.toLocalFile() for url in urls]
        self.filesDropped.emit(files)
        self.label.setText(f"已选择 {len(files)} 个文件")
        event.acceptProposedAction()

# 自定义信号类
class WorkerSignals(QObject):
    progress_signal = pyqtSignal()

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
            print(f"Error copying {self.src}: {str(e)}")
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
        
        self.output_layout.addWidget(self.output_path)
        self.output_layout.addWidget(self.browse_btn)
        
        layout.addWidget(self.drop_area)
        layout.addLayout(self.output_layout)
        self.setLayout(layout)

    def handle_files_dropped(self, files):
        self.files = files

    def select_output_path(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.output_path.setText(path)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多线程文件复制工具")
        self.setGeometry(100, 100, 800, 600)
        
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        
        self.layout = QVBoxLayout()
        self.drop_zones = []
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        
        self.add_zone_btn = QPushButton("添加拖入区域")
        self.add_zone_btn.clicked.connect(self.add_drop_zone)
        
        self.copy_btn = QPushButton("开始复制")
        self.copy_btn.clicked.connect(self.start_copy)
        
        self.layout.addWidget(self.add_zone_btn)
        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.copy_btn)
        self.main_widget.setLayout(self.layout)
        
        self.thread_pool = QThreadPool.globalInstance()
        self.total_files = 0
        self.completed_files = 0
        self.add_drop_zone()

    def add_drop_zone(self):
        drop_zone = DropZoneWidget()
        self.drop_zones.append(drop_zone)
        self.layout.insertWidget(len(self.drop_zones)-1, drop_zone)

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
        self.progress_bar.show()
        
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
                    self.thread_pool.start(worker)

    def update_progress(self):
        self.completed_files += 1
        self.progress_bar.setValue(self.completed_files)
        
        if self.completed_files == self.total_files:
            self.progress_bar.hide()
            self.copy_btn.setEnabled(True)
            self.add_zone_btn.setEnabled(True)
            QMessageBox.information(self, "完成", "文件复制完成！")
            
            # 清空拖入区但保留路径
            for zone in self.drop_zones:
                zone.files = []
                zone.drop_area.label.setText("拖放文件到这里")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())