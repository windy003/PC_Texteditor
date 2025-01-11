import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QApplication, QTextEdit, 
                           QAction, QFileDialog, QMessageBox,
                           QTabWidget)
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
        self.textChanged.connect(self.updateLineNumberWidth)
        self.modificationChanged.connect(self.handleModificationChanged)
        
    def updateLineNumberWidth(self):
        """更新行号栏的宽度"""
        lines = self.lines()
        width = max(len(str(lines)) * self.fontMetrics().width('9') + 10, 30)
        self.setMarginWidth(0, f"_{str(lines)}")  # 使用实际行数设置宽度
    
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
        
        openAction = QAction('打开(&O)', self)
        openAction.setShortcut('Ctrl+O')
        openAction.triggered.connect(self.openFile)
        fileMenu.addAction(openAction)
        
        saveAction = QAction('保存(&S)', self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.triggered.connect(self.saveFile)
        fileMenu.addAction(saveAction)
        
        viewMenu = menubar.addMenu('视图(&V)')
        
        zoomInAction = QAction('放大(&I)', self)
        zoomInAction.setShortcut('Ctrl+=')
        zoomInAction.triggered.connect(self.zoomIn)
        viewMenu.addAction(zoomInAction)
        
        zoomOutAction = QAction('缩小(&O)', self)
        zoomOutAction.setShortcut('Ctrl+-')
        zoomOutAction.triggered.connect(self.zoomOut)
        viewMenu.addAction(zoomOutAction)
        
        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle('文本编辑器')
        self.showMaximized()
    
    def currentEditor(self):
        """获取当前活动的编辑器"""
        return self.tabs.currentWidget()
    
    def newFile(self):
        editor = Editor()
        self.tabs.addTab(editor, "未命名")
        self.tabs.setCurrentWidget(editor)
    
    def openFile(self):
        fname, _ = QFileDialog.getOpenFileName(self, '打开文件', '',
            '所有文件 (*);;Python文件 (*.py);;C/C++文件 (*.c *.cpp *.h);;HTML文件 (*.html *.htm);;'
            'JavaScript文件 (*.js);;CSS文件 (*.css);;XML文件 (*.xml);;SQL文件 (*.sql)')
        if fname:
            editor = Editor()
            with open(fname, 'r', encoding='utf-8') as f:
                editor.setText(f.read())
            editor.filepath = fname
            editor.set_lexer_by_filename(fname)  # 设置语法高亮
            self.tabs.addTab(editor, os.path.basename(fname))
            self.tabs.setCurrentWidget(editor)
    
    def saveFile(self):
        editor = self.currentEditor()
        if not editor:
            return
        
        if hasattr(editor, 'filepath'):
            fname = editor.filepath
        else:
            fname, _ = QFileDialog.getSaveFileName(self, '保存文件', '',
                                                 '文本文件 (*.txt);;所有文件 (*)')
        
        if fname:
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(editor.text())
            editor.filepath = fname
            editor.modified = False  # 重置修改状态
            self.updateTabTitle(self.tabs.currentIndex())
    
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
