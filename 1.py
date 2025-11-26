import sys
import os
from PyQt5.QtWidgets import (QMainWindow, QApplication, QTextEdit,
                           QAction, QFileDialog, QMessageBox,
                           QTabWidget, QLabel, QSystemTrayIcon, QMenu,
                           QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                           QKeySequenceEdit, QFormLayout)
from PyQt5.QtGui import QIcon, QTextOption, QFont, QColor, QKeySequence
from PyQt5.QtCore import Qt, QSettings, QAbstractNativeEventFilter
from PyQt5.Qsci import (QsciScintilla, QsciLexerPython, QsciLexerCPP, 
                       QsciLexerHTML, QsciLexerJavaScript, QsciLexerCSS,
                       QsciLexerXML, QsciLexerSQL)
import winreg
import ctypes
from ctypes import wintypes

# 在文件开头添加版本号常量
VERSION = "2025/2/14-03"

# Windows 热键常量
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312

class GlobalHotkeyFilter(QAbstractNativeEventFilter):
    """全局热键事件过滤器"""
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, eventType, message):
        if eventType == "windows_generic_MSG":
            msg = wintypes.MSG.from_address(message.__int__())
            if msg.message == WM_HOTKEY:
                self.callback()
                return True, 0
        return False, 0

def resource_path(relative_path):
    """获取资源的绝对路径"""
    try:
        # PyInstaller创建临时文件夹,将路径存储在_MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 如果不是打包后的exe运行,就使用当前路径
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def is_admin():
    """检查是否具有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def add_context_menu():
    """添加右键菜单"""
    try:
        # 获取程序路径
        exe_path = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
        exe_path = f'"{exe_path}"'  # 添加引号以处理路径中的空格
        
        # 为所有文件添加右键菜单
        key_path = "*\\shell\\TextEditor"
        key = winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, key_path)
        
        # 设置默认值
        winreg.SetValue(key, "", winreg.REG_SZ, "TextEditor Context menu")
        
        # 设置显示的文本
        winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "使用文本编辑器打开(&T)")
        
        # 设置图标
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe，使用exe本身作为图标源
            exe_path = sys.executable
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{exe_path}",0')
        else:
            # 开发环境下使用icon.ico
            icon_path = resource_path("icon.ico")
            if os.path.exists(icon_path):
                abs_icon_path = os.path.abspath(icon_path)
                abs_icon_path = abs_icon_path.replace('/', '\\')
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{abs_icon_path}",0')
        
        # 创建command子键
        key_command = winreg.CreateKey(key, "command")
        winreg.SetValue(key_command, "", winreg.REG_SZ, f'{exe_path} "%1"')
        
        # 关闭键
        winreg.CloseKey(key_command)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"添加右键菜单失败: {str(e)}")
        return False

def remove_context_menu():
    """移除右键菜单"""
    try:
        key_path = "*\\shell\\TextEditor"
        # 直接删除主键即可，子键会自动删除
        winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, key_path)
        return True
    except Exception as e:
        print(f"移除右键菜单失败: {str(e)}")
        return False

class Editor(QsciScintilla):
    """单个编辑器组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = QSettings('TextEditor', 'EditorSettings')
        self.setup_editor()
        self.modified = False  # 添加修改状态标志
        self.filepath = None
        self.encoding = 'UTF-8'  # 默认编码
        self.line_ending = 'Windows (CRLF)'  # 默认换行符
        # 连接文本修改信号
        self.textChanged.connect(self.handleTextChanged)
        # 恢复缩放级别
        self.restoreZoomLevel()
        
    def setup_editor(self):
        # 设置行号显示
        self.setMarginType(0, QsciScintilla.NumberMargin)
        self.setMarginWidth(0, "0000")
        self.setMarginLineNumbers(0, True)

        # 设置字体
        self.font = QFont('Consolas', 12)
        self.setFont(self.font)

        # 设置缩放范围（-10到+20，默认是-10到+20，这里扩大到+40）
        self.SendScintilla(QsciScintilla.SCI_SETZOOM, 0)  # 设置初始缩放为0

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
        # 计算行号需要的位数，然后使用字符串设置宽度
        # QsciScintilla 会根据字符串的长度和当前字体自动计算宽度
        digits = len(str(lines))
        # 使用 '9' 字符来设置宽度，加上一些额外空间
        self.setMarginWidth(0, '9' * (digits + 2))
    
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

    def saveZoomLevel(self):
        """保存缩放级别"""
        current_zoom = self.SendScintilla(self.SCI_GETZOOM)
        self.settings.setValue('zoomLevel', current_zoom)

    def restoreZoomLevel(self):
        """恢复缩放级别"""
        zoom_level = self.settings.value('zoomLevel', 0, type=int)
        self.SendScintilla(self.SCI_SETZOOM, zoom_level)
        # 更新行号宽度以适应缩放
        self.updateLineNumberWidth()
        
class TextEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        # 使用 PNG 图标
        icon_path = resource_path("2048x2048.png")
        self.setWindowIcon(QIcon(icon_path))
        self.settings = QSettings('TextEditor', 'WindowState')
        self.hotkey_id = 1  # 热键ID
        self.initUI()
        # 托盘图标也使用相同的 PNG 图标
        self.createTrayIcon(icon_path)
        self.registerGlobalHotkey()
        self.restoreWindowState()
        
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
        
        # 添加工具菜单
        toolsMenu = menubar.addMenu('工具(&T)')

        # 添加右键菜单选项
        addContextAction = QAction('添加右键菜单(&A)', self)
        addContextAction.triggered.connect(self.addContextMenu)
        toolsMenu.addAction(addContextAction)

        # 移除右键菜单选项
        removeContextAction = QAction('移除右键菜单(&R)', self)
        removeContextAction.triggered.connect(self.removeContextMenu)
        toolsMenu.addAction(removeContextAction)
        
        # 添加帮助菜单
        helpMenu = menubar.addMenu('帮助(&H)')
        aboutAction = QAction('关于(&A)', self)
        aboutAction.triggered.connect(self.showAbout)
        helpMenu.addAction(aboutAction)
        
        self.setGeometry(300, 300, 800, 600)
        self.setWindowTitle('文本编辑器')
        
        # 添加状态栏
        self.statusBar = self.statusBar()
        self.encodingLabel = QLabel('UTF-8')
        self.lineEndingLabel = QLabel('Windows (CRLF)')
        self.statusBar.addPermanentWidget(self.encodingLabel)
        self.statusBar.addPermanentWidget(self.lineEndingLabel)

    def createTrayIcon(self, icon_path):
        """创建系统托盘图标"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(icon_path))

        # 创建托盘菜单
        tray_menu = QMenu()

        # 显示窗口动作
        show_action = QAction('显示窗口', self)
        show_action.triggered.connect(self.showMaximized)
        tray_menu.addAction(show_action)

        # 设置快捷键动作
        hotkey_action = QAction('设置唤醒快捷键(&H)', self)
        hotkey_action.triggered.connect(self.showHotkeyDialog)
        tray_menu.addAction(hotkey_action)

        tray_menu.addSeparator()

        # 退出动作
        quit_action = QAction('退出(&X)', self)
        quit_action.triggered.connect(self.quitApplication)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)

        # 双击托盘图标显示窗口
        self.tray_icon.activated.connect(self.trayIconActivated)

        # 显示托盘图标
        self.tray_icon.show()

    def trayIconActivated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.showMaximized()
            self.activateWindow()

    def currentEditor(self):
        """获取当前活动的编辑器"""
        return self.tabs.currentWidget()
    
    def newFile(self):
        editor = Editor()
        self.tabs.addTab(editor, "未命名")
        self.tabs.setCurrentWidget(editor)
        # 设置焦点到编辑器
        editor.setFocus()
    
    def openFile(self, filepath=None):
        """打开文件"""
        if filepath is None:
            fname, _ = QFileDialog.getOpenFileName(self, '打开文件', '',
                '所有文件 (*);;Python文件 (*.py);;C/C++文件 (*.c *.cpp *.h);;HTML文件 (*.html *.htm);;'
                'JavaScript文件 (*.js);;CSS文件 (*.css);;XML文件 (*.xml);;SQL文件 (*.sql)')
        else:
            fname = filepath
            
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
                # 先将所有换行符统一为\n
                text = text.replace('\r\n', '\n')  # 将Windows换行符转换为\n
                text = text.replace('\r', '\n')    # 将Mac换行符转换为\n

                # 根据当前设置的换行符类型进行转换
                if editor.line_ending == 'Windows (CRLF)':
                    text = text.replace('\n', '\r\n')  # 转换为Windows格式
                elif editor.line_ending == 'Unix (LF)':
                    pass  # 已经是Unix格式，无需转换
                elif editor.line_ending == 'Mac (CR)':
                    text = text.replace('\n', '\r')  # 转换为Mac格式
                
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
            # 获取当前缩放级别
            current_zoom = editor.SendScintilla(editor.SCI_GETZOOM)
            # 设置新的缩放级别，最大可到 100
            new_zoom = min(current_zoom + 3, 100)
            editor.SendScintilla(editor.SCI_SETZOOM, new_zoom)
            # 更新行号宽度以适应缩放后的字体
            editor.updateLineNumberWidth()
            # 保存缩放级别
            editor.saveZoomLevel()

    def zoomOut(self):
        if editor := self.currentEditor():
            # 获取当前缩放级别
            current_zoom = editor.SendScintilla(editor.SCI_GETZOOM)
            # 设置新的缩放级别，最小可到 -10
            new_zoom = max(current_zoom - 3, -10)
            editor.SendScintilla(editor.SCI_SETZOOM, new_zoom)
            # 更新行号宽度以适应缩放后的字体
            editor.updateLineNumberWidth()
            # 保存缩放级别
            editor.saveZoomLevel()
    
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
    
    def showAbout(self):
        """显示关于对话框"""
        QMessageBox.about(self, 
            '关于文本编辑器',
            f'文本编辑器 v{VERSION}\n\n'
            '一个简单而强大的文本编辑器\n'
            '支持多种编程语言的语法高亮\n'
            )
    
    def addContextMenu(self):
        """添加右键菜单的处理函数"""
        if not is_admin():
            QMessageBox.warning(self, '权限不足', '添加右键菜单需要管理员权限。\n请以管理员身份运行程序。')
            return
        
        if add_context_menu():
            QMessageBox.information(self, '成功', '右键菜单添加成功！')
        else:
            QMessageBox.warning(self, '失败', '右键菜单添加失败！')
    
    def removeContextMenu(self):
        """移除右键菜单的处理函数"""
        if not is_admin():
            QMessageBox.warning(self, '权限不足', '移除右键菜单需要管理员权限。\n请以管理员身份运行程序。')
            return

        if remove_context_menu():
            QMessageBox.information(self, '成功', '右键菜单移除成功！')
        else:
            QMessageBox.warning(self, '失败', '右键菜单移除失败！')

    def registerGlobalHotkey(self):
        """注册全局热键"""
        # 获取保存的热键设置，默认为 Ctrl+Alt+T
        hotkey_str = self.settings.value('globalHotkey', 'Ctrl+Alt+T')

        # 解析热键字符串
        modifiers, key = self.parseHotkey(hotkey_str)

        if modifiers is not None and key is not None:
            # 注册热键
            hwnd = int(self.winId())

            # 先尝试注销可能存在的旧热键
            ctypes.windll.user32.UnregisterHotKey(hwnd, self.hotkey_id)

            # 注册新热键
            result = ctypes.windll.user32.RegisterHotKey(hwnd, self.hotkey_id, modifiers, key)
            if result:
                # 安装事件过滤器
                if not hasattr(self, 'hotkey_filter'):
                    self.hotkey_filter = GlobalHotkeyFilter(self.onGlobalHotkey)
                    QApplication.instance().installNativeEventFilter(self.hotkey_filter)
            else:
                # 静默失败，不弹窗警告，只在日志中记录
                print(f'无法注册全局热键 {hotkey_str}，可能已被其他程序占用。')

    def unregisterGlobalHotkey(self):
        """注销全局热键"""
        try:
            hwnd = int(self.winId())
            ctypes.windll.user32.UnregisterHotKey(hwnd, self.hotkey_id)
        except:
            # 忽略注销失败的错误
            pass

    def parseHotkey(self, hotkey_str):
        """解析热键字符串，返回修饰符和按键码"""
        if not hotkey_str:
            return None, None

        key_sequence = QKeySequence(hotkey_str)
        if key_sequence.isEmpty():
            return None, None

        # 获取第一个按键
        key_code = key_sequence[0]

        modifiers = 0
        # 检查修饰符
        if key_code & Qt.CTRL:
            modifiers |= MOD_CONTROL
        if key_code & Qt.ALT:
            modifiers |= MOD_ALT
        if key_code & Qt.SHIFT:
            modifiers |= MOD_SHIFT
        if key_code & Qt.META:
            modifiers |= MOD_WIN

        # 获取实际按键（去除修饰符）
        key = key_code & ~(Qt.CTRL | Qt.ALT | Qt.SHIFT | Qt.META)

        # 转换Qt按键码到Windows虚拟键码
        vk_code = self.qtKeyToVK(key)

        return modifiers, vk_code

    def qtKeyToVK(self, qt_key):
        """将Qt按键码转换为Windows虚拟键码"""
        # 字母和数字键
        if Qt.Key_A <= qt_key <= Qt.Key_Z:
            return ord('A') + (qt_key - Qt.Key_A)
        if Qt.Key_0 <= qt_key <= Qt.Key_9:
            return ord('0') + (qt_key - Qt.Key_0)

        # F功能键
        if Qt.Key_F1 <= qt_key <= Qt.Key_F24:
            return 0x70 + (qt_key - Qt.Key_F1)

        # 其他常用键
        key_map = {
            Qt.Key_Space: 0x20,
            Qt.Key_Return: 0x0D,
            Qt.Key_Escape: 0x1B,
            Qt.Key_Tab: 0x09,
            Qt.Key_Backspace: 0x08,
        }

        return key_map.get(qt_key, qt_key & 0xFFFF)

    def onGlobalHotkey(self):
        """全局热键回调"""
        if self.isVisible():
            self.hide()
        else:
            self.showMaximized()
            self.activateWindow()

    def showHotkeyDialog(self):
        """显示热键设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle('设置唤醒快捷键')
        dialog.setModal(True)

        layout = QVBoxLayout()

        # 创建表单布局
        form_layout = QFormLayout()

        # 热键输入框
        hotkey_edit = QKeySequenceEdit()
        current_hotkey = self.settings.value('globalHotkey', 'Ctrl+Alt+T')
        hotkey_edit.setKeySequence(QKeySequence(current_hotkey))

        form_layout.addRow('快捷键:', hotkey_edit)
        layout.addLayout(form_layout)

        # 按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton('确定')
        cancel_button = QPushButton('取消')

        def on_ok():
            new_hotkey = hotkey_edit.keySequence().toString()
            if new_hotkey:
                self.settings.setValue('globalHotkey', new_hotkey)
                self.registerGlobalHotkey()
                QMessageBox.information(self, '成功', f'全局热键已设置为: {new_hotkey}')
                dialog.accept()
            else:
                QMessageBox.warning(self, '警告', '请输入有效的快捷键')

        ok_button.clicked.connect(on_ok)
        cancel_button.clicked.connect(dialog.reject)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec_()

    def restoreWindowState(self):
        """恢复窗口状态"""
        # 恢复窗口几何信息（位置和大小）
        geometry = self.settings.value('geometry')
        if geometry:
            self.restoreGeometry(geometry)

        # 恢复窗口状态（最大化、最小化等）
        window_state = self.settings.value('windowState')
        if window_state:
            self.restoreState(window_state)

        # 恢复是否最大化
        is_maximized = self.settings.value('isMaximized', True, type=bool)
        if is_maximized:
            self.showMaximized()
        else:
            self.show()

    def saveWindowState(self):
        """保存窗口状态"""
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('windowState', self.saveState())
        self.settings.setValue('isMaximized', self.isMaximized())

    def closeEvent(self, event):
        """窗口关闭事件 - 最小化到托盘"""
        if self.tray_icon.isVisible():
            # 隐藏窗口到托盘
            self.hide()
            self.saveWindowState()
            event.ignore()  # 阻止窗口关闭
        else:
            self.saveWindowState()
            event.accept()

    def quitApplication(self):
        """真正退出应用程序"""
        self.saveWindowState()
        self.unregisterGlobalHotkey()  # 注销全局热键
        self.tray_icon.hide()  # 隐藏托盘图标
        QApplication.quit()  # 退出应用

    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        self.saveWindowState()

    def moveEvent(self, event):
        """窗口移动事件"""
        super().moveEvent(event)
        self.saveWindowState()

    def changeEvent(self, event):
        """窗口状态改变事件（最大化、最小化等）"""
        super().changeEvent(event)
        if event.type() == event.WindowStateChange:
            self.saveWindowState()

if __name__ == '__main__':
    # 切换工作目录到脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 如果没有管理员权限，请求管理员权限重新运行
    # if not is_admin():
    #     ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    #     sys.exit()

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("2048x2048.png")))
    editor = TextEditor()
    
    # 如果是第一次运行，添加右键菜单
    if len(sys.argv) == 1:  # 没有命令行参数时尝试添加右键菜单
        add_context_menu()
    
    # 如果有文件路径参数，打开该文件
    if len(sys.argv) > 1:
        editor.openFile(sys.argv[1])
    
    sys.exit(app.exec_())
