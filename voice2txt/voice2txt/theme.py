"""淺色／深色外觀。apply 可重複呼叫以在執行中切換。"""
import tkinter as tk
from tkinter import ttk

LIGHT = {'bg': '#f3f3f3', 'panel': '#ffffff', 'fg': '#1f1f1f', 'muted': '#6b6b6b',
         'accent': '#0f6cbd', 'text_bg': '#ffffff', 'text_fg': '#1f1f1f',
         'list_bg': '#ffffff', 'select_bg': '#cce4f7'}
DARK = {'bg': '#202020', 'panel': '#2b2b2b', 'fg': '#f0f0f0', 'muted': '#a0a0a0',
        'accent': '#4cc2ff', 'text_bg': '#1b1b1b', 'text_fg': '#f0f0f0',
        'list_bg': '#252525', 'select_bg': '#3a5a78'}
CHOICES = ('系統', '淺色', '深色')


def system_prefers_dark():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
            return winreg.QueryValueEx(key, 'AppsUseLightTheme')[0] == 0
    except Exception:
        return False


def resolve(choice):
    if choice == '深色':
        return DARK
    if choice == '淺色':
        return LIGHT
    return DARK if system_prefers_dark() else LIGHT


def apply(style, root, palette, widgets=()):
    try:
        if style.theme_use() != 'clam':
            style.theme_use('clam')
    except tk.TclError:
        pass
    p = palette
    root.configure(bg=p['bg'])
    style.configure('.', background=p['bg'], foreground=p['fg'], fieldbackground=p['text_bg'],
                    troughcolor=p['panel'], bordercolor=p['muted'], lightcolor=p['panel'],
                    darkcolor=p['panel'], insertcolor=p['fg'])
    style.map('.', foreground=[('disabled', p['muted'])])
    style.configure('TFrame', background=p['bg'])
    style.configure('TLabel', background=p['bg'], foreground=p['fg'])
    style.configure('TButton', background=p['panel'], foreground=p['fg'])
    style.map('TButton', background=[('active', p['select_bg'])],
              foreground=[('disabled', p['muted'])])
    style.configure('TNotebook', background=p['bg'])
    style.configure('TNotebook.Tab', background=p['panel'], foreground=p['fg'])
    style.map('TNotebook.Tab', background=[('selected', p['accent'])],
              foreground=[('selected', p['bg'])])
    style.configure('TCheckbutton', background=p['bg'], foreground=p['fg'])
    style.map('TCheckbutton', background=[('active', p['bg'])])
    style.configure('TCombobox', fieldbackground=p['text_bg'], background=p['panel'],
                    foreground=p['text_fg'], arrowcolor=p['fg'])
    style.map('TCombobox', fieldbackground=[('readonly', p['text_bg'])],
              foreground=[('readonly', p['text_fg'])])
    for w in widgets:
        if isinstance(w, tk.Text):
            w.configure(bg=p['text_bg'], fg=p['text_fg'], insertbackground=p['text_fg'],
                        selectbackground=p['select_bg'], selectforeground=p['text_fg'])
        elif isinstance(w, tk.Listbox):
            w.configure(bg=p['list_bg'], fg=p['text_fg'], selectbackground=p['select_bg'],
                        selectforeground=p['text_fg'])
        elif isinstance(w, tk.Canvas):
            w.configure(bg=p['bg'], highlightbackground=p['bg'])
