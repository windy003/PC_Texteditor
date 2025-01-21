import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QApplication, QTextEdit, 
                           QAction, QFileDialog, QMessageBox,
                           QTabWidget, QLabel)
from PyQt5.QtGui import QIcon, QTextOption, QFont, QColor
from PyQt5.QtCore import Qt
from PyQt5.Qsci import (QsciScintilla, QsciLexerPython, QsciLexerCPP, 
                       QsciLexerHTML, QsciLexerJavaScript, QsciLexerCSS,
                       QsciLexerXML, QsciLexerSQL)

def resource_path(relative_path):
    """获取资源的绝对路径"""
    try:
        # PyInstaller创建临时文件夹,将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 如果不是打包后的exe运行,就使用当前路径
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class Editor(QsciScintilla):
    """单个编辑器组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_editor()
        self.modified = False  # 添加修改状态标志
        self.filepath = None
        self.encoding = 'UTF-8'  # 默认编码
        self.line_ending = 'Windows (CRLF)'  # 默认换行符
        # 连接文本修改信号
        self.textChanged.connect(self.handleTextChanged)
        
    def setup_editor(self):
        # 设置行号显示
        self.setMarginType(0, QsciScintilla.NumberMargin)
        self.setMarginWidth(0, "0000")
        self.setMarginLineNumbers(0, True)
        
        # 设置字体
        self.font = QFont('Consolas', 12)
        self.setFont(self.font)
        
        # 设置自动缩进
        self.setAutoIndent(True)
        self.setIndentationGuides(True)
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        
        # 设置括号匹配
        self.setBraceMatching(QsciScintilla.SloppyBraceMatch)
        
        # 设置当前行高亮
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor("#e8e8e8"))
        
        # 连接信号
        self.modificationChanged.connect(self.handleModificationChanged)
        
    def handleTextChanged(self):
        """处理文本变化"""
        self.modified = True
        self.updateLineNumberWidth()
        # 通知父窗口更新标签
        main_window = self.get_main_window()
        if main_window:
            index = main_window.tabs.indexOf(self)
            main_window.updateTabTitle(index)
    
    def handleModificationChanged(self, modified):
        """处理文本修改状态改变"""
        self.modified = modified
        # 通知父窗口更新标签
        if hasattr(self, 'parent'):
            parent = self.parent()
            while parent and not isinstance(parent, TextEditor):
                parent = parent.parent()
            if parent:
                index = parent.tabs.indexOf(self)
                parent.updateTabTitle(index)
    
    def set_lexer_by_filename(self, filename):
        """根据文件名设置对应的语法高亮"""
        if not filename:
            return
            
        ext = os.path.splitext(filename)[1].lower()
        lexer = None
        
        if ext in ['.py', '.pyw']:
            lexer = QsciLexerPython(self)
        elif ext in ['.c', '.cpp', '.h', '.hpp']:
            lexer = QsciLexerCPP(self)
        elif ext in ['.html', '.htm']:
            lexer = QsciLexerHTML(self)
        elif ext == '.js':
            lexer = QsciLexerJavaScript(self)
        elif ext == '.css':
            lexer = QsciLexerCSS(self)
        elif ext == '.xml':
            lexer = QsciLexerXML(self)
        elif ext == '.sql':
            lexer = QsciLexerSQL(self)
            
        if lexer:
            # 设置lexer的字体
            lexer.setFont(self.font)
            self.setLexer(lexer)
    
    def detect_line_ending(self, text):
        """检测文本的换行符类型"""
        if '\r\n' in text:
            self.line_ending = 'Windows (CRLF)'
        elif '\n' in text:
            self.line_ending = 'Unix (LF)'
        elif '\r' in text:
            self.line_ending = 'Mac (CR)'
        else:
            self.line_ending = 'Windows (CRLF)'  # 默认值
            
    def setText(self, text):
        """重写 setText 方法以检测换行符"""
        self.detect_line_ending(text)
        super().setText(text)
        # 通知父窗口更新状态栏
        if hasattr(self, 'parent'):
            parent = self.parent()
            while parent and not isinstance(parent, TextEditor):
                parent = parent.parent()
            if parent:
                parent.updateStatusBar()

    def updateLineNumberWidth(self):
        """更新行号栏的宽度"""
        lines = self.lines()
        width = max(len(str(lines)) * self.fontMetrics().width('9') + 10, 30)
        self.setMarginWidth(0, width)  # 使用计算出的width值设置边距宽度
    
    def keyPressEvent(self, event):
        """处理按键事件"""
        # 检查是否按下了 Ctrl+X
        if event.key() == Qt.Key_X and event.modifiers() == Qt.ControlModifier:
            if not self.hasSelectedText():
                # 如果没有选中文本，执行剪切整行
                line, _ = self.getCursorPosition()
                # 获取当前行的内容
                text = self.text(line)
                # 选中整行
                line_length = len(text)
                self.setSelection(line, 0, line, line_length)
                # 剪切选中内容
                super().keyPressEvent(event)
            else:
                # 如果有选中的文本，执行普通的剪切操作
                super().keyPressEvent(event)
        # 检查是否按下了 Ctrl+S
        elif event.key() == Qt.Key_S and event.modifiers() == Qt.ControlModifier:
            # 获取主窗口并调用保存方法
            main_window = self.get_main_window()
            if main_window:
                main_window.saveFile()
            event.accept()
        else:
            # 其他按键保持默认行为
            super().keyPressEvent(event)
            
    def get_main_window(self):
        """获取主窗口实例"""
        parent = self.parent()
        while parent:
            if isinstance(parent, TextEditor):
                return parent
            parent = parent.parent()
        return None
        
class TextEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        icon_path = resource_path("icon.ico")
        self.setWindowIcon(QIcon(icon_path))
        self.initUI()
        
    def initUI(self):
        # 创建标签页组件
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)  # 允许关闭标签
        self.tabs.tabCloseRequested.connect(self.closeTab)
        self.setCentralWidget(self.tabs)
        
        # 创建第一个标签页
        self.newFile()
        
        # 创建菜单栏
        menubar = self.menuBar()
        
        fileMenu = menubar.addMenu('文件(&F)')
        
        newAction = QAction('新建(&N)', self)
        newAction.setShortcut('Ctrl+N')
        newAction.triggered.connect(self.newFile)
        fileMenu.addAction(newAction)
        
        # 添加新建标签的快捷键动作
        newTabAction = QAction('新建标签(&T)', self)
        newTabAction.setShortcut('Ctrl+T')
        newTabAction.triggered.connect(self.newFile)  # 复用 newFile 方法
        fileMenu.addAction(newTabAction)
        
        openAction = QAction('打开(&O)', self)
        openAction.setShortcut('Ctrl+O')
        openAction.triggered.connect(self.openFile)
        fileMenu.addAction(openAction)
        
        saveAction = QAction('保存(&S)', self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.triggered.connect(self.saveFile)
        fileMenu.addAction(saveAction)
        
        # 添加关闭标签的动作
        closeTabAction = QAction('关闭标签(&W)', self)
        closeTabAction.setShortcut('Ctrl+W')
        closeTabAction.triggered.connect(self.closeCurrentTab)
        fileMenu.addAction(closeTabAction)
        
        viewMenu = menubar.addMenu('视图(&V)')
        
        zoomInAction = QAction('放大(&I)', self)
        zoomInAction.setShortcut('Ctrl+=')
        zoomInAction.triggered.connect(self.zoomIn)
        viewMenu.addAction(zoomInAction)
        
        zoomOutAction = QAction('缩小(&O)', self)
        zoomOutAction.setShortcut('Ctrl+-')
        zoomOutAction.triggered.connect(self.zoomOut)
        viewMenu.addAction(zoomOutAction)
        
        # 添加标签切换动作
        nextTabAction = QAction('下一个标签页', self)
        nextTabAction.setShortcut('Ctrl+PgDown')
        nextTabAction.triggered.connect(self.nextTab)
        
        prevTabAction = QAction('上一个标签页', self)
        prevTabAction.setShortcut('Ctrl+PgUp')
        prevTabAction.triggered.connect(self.prevTab)
        
        # 将动作添加到窗口，但不显示在菜单中
        self.addAction(nextTabAction)
        self.addAction(prevTabAction)
        
        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle('文本编辑器')
        self.showMaximized()
        
        # 添加状态栏
        self.statusBar = self.statusBar()
        self.encodingLabel = QLabel('UTF-8')
        self.lineEndingLabel = QLabel('Windows (CRLF)')
        self.statusBar.addPermanentWidget(self.encodingLabel)
        self.statusBar.addPermanentWidget(self.lineEndingLabel)
    
    def currentEditor(self):
        """获取当前活动的编辑器"""
        return self.tabs.currentWidget()
    
    def newFile(self):
        editor = Editor()
        self.tabs.addTab(editor, "未命名")
        self.tabs.setCurrentWidget(editor)
        # 设置焦点到编辑器
        editor.setFocus()
    
    def openFile(self):
        fname, _ = QFileDialog.getOpenFileName(self, '打开文件', '',
            '所有文件 (*);;Python文件 (*.py);;C/C++文件 (*.c *.cpp *.h);;HTML文件 (*.html *.htm);;'
            'JavaScript文件 (*.js);;CSS文件 (*.css);;XML文件 (*.xml);;SQL文件 (*.sql)')
        if fname:
            editor = Editor()
            try:
                # 以二进制模式读取文件以检测换行符
                with open(fname, 'rb') as f:
                    content = f.read()
                    
                # 检测文件的换行符类型
                if b'\r\n' in content:
                    editor.line_ending = 'Windows (CRLF)'
                    text = content.decode(editor.encoding).replace('\r\n', '\n')
                elif b'\n' in content:
                    editor.line_ending = 'Unix (LF)'
                    text = content.decode(editor.encoding)
                elif b'\r' in content:
                    editor.line_ending = 'Mac (CR)'
                    text = content.decode(editor.encoding).replace('\r', '\n')
                else:
                    editor.line_ending = 'Windows (CRLF)'  # 默认值
                    text = content.decode(editor.encoding)
                    
            except UnicodeDecodeError:
                try:
                    editor.encoding = 'GBK'
                    text = content.decode(editor.encoding)
                except:
                    QMessageBox.warning(self, '错误', '无法识别文件编码')
                    return
                    
            editor.setText(text)
            editor.filepath = fname
            editor.set_lexer_by_filename(fname)
            self.tabs.addTab(editor, os.path.basename(fname))
            self.tabs.setCurrentWidget(editor)
            self.updateStatusBar()
            # 设置焦点到编辑器
            editor.setFocus()
    
    def saveFile(self):
        editor = self.currentEditor()
        if not editor:
            return
            
        if editor.filepath:
            fname = editor.filepath
        else:
            fname, _ = QFileDialog.getSaveFileName(self, '保存文件', '',
                                                 '文本文件 (*.txt);;所有文件 (*)')
            
        if fname:
            try:
                # 获取文本并规范化换行符
                text = editor.text()
                # 根据当前设置的换行符类型进行转换
                if editor.line_ending == 'Windows (CRLF)':
                    text = text.replace('\n', '\r\n')
                elif editor.line_ending == 'Unix (LF)':
                    text = text.replace('\r\n', '\n')
                elif editor.line_ending == 'Mac (CR)':
                    text = text.replace('\n', '\r')
                
                with open(fname, 'w', encoding='utf-8', newline='') as f:
                    f.write(text)
                editor.filepath = fname
                editor.modified = False  # 重置修改状态
                self.updateTabTitle(self.tabs.currentIndex())
                # 显示保存成功消息
                self.statusBar.showMessage('文件已保存', 2000)  # 显示2秒
                return True
            except Exception as e:
                QMessageBox.warning(self, '保存失败', f'保存文件时发生错误：{str(e)}')
                return False
        return False
    
    def closeTab(self, index):
        if self.tabs.count() > 1:  # 保持至少一个标签页
            self.tabs.removeTab(index)
        
    def zoomIn(self):
        if editor := self.currentEditor():
            editor.zoomIn()
    
    def zoomOut(self):
        if editor := self.currentEditor():
            editor.zoomOut()
    
    def updateTabTitle(self, index):
        """更新标签标题，添加修改标记"""
        editor = self.tabs.widget(index)
        current_text = self.tabs.tabText(index)
        
        # 移除可能存在的修改标记
        if current_text.endswith('*'):
            current_text = current_text[:-1]
            
        # 如果有修改则添加星号
        if editor.modified:
            self.tabs.setTabText(index, current_text + '*')
        else:
            self.tabs.setTabText(index, current_text)
    
    def closeCurrentTab(self):
        """关闭当前标签页"""
        current_index = self.tabs.currentIndex()
        if self.tabs.count() > 1:  # 保持至少一个标签页
            self.tabs.removeTab(current_index)
    
    def nextTab(self):
        """切换到下一个标签页"""
        current = self.tabs.currentIndex()
        if current < self.tabs.count() - 1:
            self.tabs.setCurrentIndex(current + 1)
        else:
            self.tabs.setCurrentIndex(0)
    
    def prevTab(self):
        """切换到上一个标签页"""
        current = self.tabs.currentIndex()
        if current > 0:
            self.tabs.setCurrentIndex(current - 1)
        else:
            self.tabs.setCurrentIndex(self.tabs.count() - 1)
    
    def updateStatusBar(self):
        """更新状态栏信息"""
        editor = self.currentEditor()
        if editor:
            self.encodingLabel.setText(editor.encoding)
            self.lineEndingLabel.setText(editor.line_ending)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("icon.ico")))
    editor = TextEditor()
    
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if os.path.exists(filepath):
            new_editor = Editor()
            with open(filepath, 'r', encoding='utf-8') as f:
                new_editor.setText(f.read())
            new_editor.filepath = filepath
            new_editor.set_lexer_by_filename(filepath)  # 设置语法高亮
            editor.tabs.addTab(new_editor, os.path.basename(filepath))
            editor.tabs.setCurrentWidget(new_editor)
            editor.tabs.removeTab(0)
    
    sys.exit(app.exec_())
