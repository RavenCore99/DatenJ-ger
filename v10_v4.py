#  ______-_______ ALPHA V1.0 - LAUNCH TEST ____-___ #
#   Sistema de Gestión Documental de PDFs Y manejo de datos de personas
#Prototipo en fase de desarrollo inicial | Idea, desarrollo hechos por Nicolas Ballesteros
                                # |Presentado a la Universidad de CUndinamarca| Seccional Ubate | Colombia | 


import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog, Toplevel
from tkinter.ttk import Progressbar
import os
import tempfile
import webbrowser  # Para abrir PDFs
from datetime import datetime
import hashlib  # Para hashing de contraseñas
from PIL import ImageTk, Image  # Añadido para manejar imágenes
import random  # Para colores aleatorios
import sys  # Para detección de plataforma

# Función de conexión a BD con corrección para agregar columna contrasena y nueva tabla Personas
def conectar_db():
    conn = sqlite3.connect('base_datos_pdfs.db')
    cursor = conn.cursor()
    
    # Crear tablas e índices
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            contrasena TEXT NOT NULL  -- Hash de la contraseña
        )
    ''')
    # Verificar y agregar columna contrasena si no existe
    cursor.execute("PRAGMA table_info(Usuarios)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'contrasena' not in columns:
        cursor.execute("ALTER TABLE Usuarios ADD COLUMN contrasena TEXT NOT NULL DEFAULT ''")
        conn.commit()  # Confirmar la alteración

    # Nueva tabla Personas para clasificación detallada
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cedula TEXT NOT NULL UNIQUE,
            nombres TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PDFs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT,
            datos BLOB NOT NULL,
            tamano INTEGER NOT NULL,
            fecha_subida TEXT NOT NULL,
            usuario_id INTEGER,
            persona_id INTEGER,  -- Nueva clave foránea para asociación detallada
            FOREIGN KEY (usuario_id) REFERENCES Usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY (persona_id) REFERENCES Personas(id) ON DELETE SET NULL
        )
    ''')
    # Verificar y agregar columna persona_id si no existe
    cursor.execute("PRAGMA table_info(PDFs)")
    columns_pdf = [col[1] for col in cursor.fetchall()]
    if 'persona_id' not in columns_pdf:
        cursor.execute("ALTER TABLE PDFs ADD COLUMN persona_id INTEGER REFERENCES Personas(id) ON DELETE SET NULL")
        conn.commit()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Etiquetas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS PDF_Etiquetas (
            pdf_id INTEGER,
            etiqueta_id INTEGER,
            PRIMARY KEY (pdf_id, etiqueta_id),
            FOREIGN KEY (pdf_id) REFERENCES PDFs(id) ON DELETE CASCADE,
            FOREIGN KEY (etiqueta_id) REFERENCES Etiquetas(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            accion TEXT NOT NULL,
            pdf_id INTEGER,
            usuario_id INTEGER,
            fecha TEXT NOT NULL
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pdfs_usuario ON PDFs(usuario_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pdfs_fecha ON PDFs(fecha_subida)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pdfs_persona ON PDFs(persona_id)')  # Nuevo índice para consultas por persona
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON Auditoria(fecha)')
    
    conn.commit()
    return conn, cursor

# Función para hashear contraseña
def hash_contrasena(contrasena):
    return hashlib.sha256(contrasena.encode()).hexdigest()

# Función para generar color aleatorio en grises y azules
def random_gray_blue():
    base = random.choice(['gray', 'blue'])
    if base == 'gray':
        shade = random.randint(50, 200)
        return f'#{shade:02x}{shade:02x}{shade:02x}'
    else:
        r = random.randint(0, 100)
        g = random.randint(100, 200)
        b = random.randint(150, 255)
        return f'#{r:02x}{g:02x}{b:02x}'

# Función de easing out para animaciones
def ease_out(t):
    return 1 - (1 - t) ** 2

# Clase principal con diseño mejorado y credenciales
class AppDBPDF:
    def __init__(self, root):
        self.root = root
        self.root.title("DatenJäger - Sistema de Gestion Documental")
        self.root.geometry("800x600")
        self.root.configure(bg='#F5F5F5')  # Fondo gris claro para todas las ventanas
        if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
        else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
        
        # Estilo ttk para tema moderno
        style = ttk.Style()
        style.theme_use('clam')  # Tema atractivo
        style.configure('TButton', font=('Arial', 12, 'bold'), padding=15)  # Botones más grandes
        style.configure('TLabel', font=('Arial', 11, 'bold'), background='#F5F5F5')
        style.configure('Treeview', font=('Arial', 9), rowheight=25)
        style.configure('Treeview.Heading', font=('Arial', 10, 'bold'))
        
        self.conn, self.cursor = conectar_db()
        self.usuario_actual = None
        self.animating = False  # Control de animaciones
        
        # Interfaz previa (intro screen) con animaciones
        self.frame_intro = tk.Frame(root, bg='#2c2434')  # Fondo #2c2434
        self.frame_intro.pack(expand=True, fill='both')
        
        # Texto animado con estilo gótico (usa una fuente serif bold para simular gótico)
        try:
            self.intro_text = tk.Label(self.frame_intro, text="DatenJäger | Gestor de PDFs |", font=('Old English Text MT', 36, 'bold'), fg='white', bg='#2c2434')
        except:
            self.intro_text = tk.Label(self.frame_intro, text="DatenJäger | Gestor de PDFs |", font=('Times New Roman', 36, 'bold'), fg='white', bg='#2c2434')  # Fallback
        self.intro_text.pack(expand=True)
        self.intro_text.bind("<Button-1>", self.on_intro_click)  # Clic en texto para acceder
        
        # Texto para acceder (con animación fluida)
        self.access_text = tk.Label(self.frame_intro, text="Alpha V1.0 |Lauch Test|", bg='#2c2434', cursor="hand2")
        try:
            self.access_text.config(font=('Old English Text MT', 20, 'bold'), fg='white')
        except:
            self.access_text.config(font=('Times New Roman', 20, 'bold'), fg='white')
        self.access_text.pack(pady=20)
        self.access_text.bind("<Button-1>", self.on_intro_click)
        self.access_scale = 1.0
        self.animate_access_text()
        
        # Animación suave para el texto de intro (fade in)
        self.intro_alpha = 0.0
        self.fade_in_text(self.intro_text)
        
        # Ciclo de colores lento para el fondo con fade out
        self.colors = ['#2c2434', '#3a3145', '#483e56', '#564b67', '#645878', '#726589', '#80729a', '#8e7fab', '#9c8cbc', '#aa99cd']
        self.current_color_index = 0
        self.fade_background()
        
        # Frame inicial con opciones (oculto inicialmente)
        self.frame_inicial = tk.Frame(root, bg='#F5F5F5', padx=20, pady=20)
        
        tk.Label(self.frame_inicial, text="DatenJäger <Gestor de PDF>", font=('Arial', 16, 'bold'), bg='#F5F5F5', fg='#00695C').pack(pady=10)
        
        btn_iniciar = tk.Button(self.frame_inicial, text="Iniciar Sesión", command=self.mostrar_login, bg='#4CAF50', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        btn_iniciar.pack(pady=15)
        btn_iniciar.bind("<Enter>", lambda e: self.animate_button(btn_iniciar, 'enter'))
        btn_iniciar.bind("<Leave>", lambda e: self.animate_button(btn_iniciar, 'leave'))
        
        btn_registrar = tk.Button(self.frame_inicial, text="Crear Usuario", command=self.mostrar_registro, bg='#2196F3', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        btn_registrar.pack(pady=15)
        btn_registrar.bind("<Enter>", lambda e: self.animate_button(btn_registrar, 'enter'))
        btn_registrar.bind("<Leave>", lambda e: self.animate_button(btn_registrar, 'leave'))
        
        btn_recuperar = tk.Button(self.frame_inicial, text="Recuperar Contraseña", command=self.mostrar_recuperar, bg='#FF9800', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        btn_recuperar.pack(pady=15)
        btn_recuperar.bind("<Enter>", lambda e: self.animate_button(btn_recuperar, 'enter'))
        btn_recuperar.bind("<Leave>", lambda e: self.animate_button(btn_recuperar, 'leave'))
        
        # Frame dedicado para iniciar sesión
        self.frame_login = tk.Frame(root, bg='#F5F5F5', padx=20, pady=20)
        # Añadir logo centrado
        # Añadir logo centrado
        try:
            img_path = os.path.join(base_path, "logo.png")  # CAMBIA ESTA RUTA A TU IMAGEN
            img = Image.open(img_path)
            img = img.resize((200, 100), Image.Resampling.LANCZOS)
            self.logo_image = ImageTk.PhotoImage(img)
            logo_label = tk.Label(self.frame_login, image=self.logo_image, bg='#F5F5F5')
            logo_label.place(relx=0.5, rely=0.05, anchor="center")
        except FileNotFoundError:
            messagebox.showerror("Error", "Imagen del logo no encontrada. Actualiza la ruta en el código.", parent=self.root)
        tk.Label(self.frame_login, text="Iniciar Sesión", font=('Arial', 16, 'bold'), bg='#F5F5F5', fg='#00695C').pack(pady=10)
        tk.Label(self.frame_login, text="Nombre de Usuario:", bg='#F5F5F5', fg='#004D40').pack()
        self.entry_usuario_login = tk.Entry(self.frame_login, font=('Arial', 12), width=20)
        self.entry_usuario_login.pack(pady=5)
        tk.Label(self.frame_login, text="Contraseña:", bg='#F5F5F5', fg='#004D40').pack()
        self.entry_contrasena_login = tk.Entry(self.frame_login, font=('Arial', 12), width=20, show='*')
        self.entry_contrasena_login.pack(pady=5)
        login_btn = tk.Button(self.frame_login, text="Iniciar", command=self.login, bg='#4CAF50', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        login_btn.pack(pady=15)
        login_btn.bind("<Enter>", lambda e: self.animate_button(login_btn, 'enter'))
        login_btn.bind("<Leave>", lambda e: self.animate_button(login_btn, 'leave'))
        volver_btn = tk.Button(self.frame_login, text="Volver", command=self.mostrar_inicial, bg='#9E9E9E', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        volver_btn.pack()
        volver_btn.bind("<Enter>", lambda e: self.animate_button(volver_btn, 'enter'))
        volver_btn.bind("<Leave>", lambda e: self.animate_button(volver_btn, 'leave'))
        
        # Frame dedicado para crear usuario
        self.frame_registro = tk.Frame(root, bg='#F5F5F5', padx=20, pady=20)
        tk.Label(self.frame_registro, text="Crear Usuario", font=('Arial', 16, 'bold'), bg='#F5F5F5', fg='#00695C').pack(pady=10)
        tk.Label(self.frame_registro, text="Nombre de Usuario:", bg='#F5F5F5', fg='#004D40').pack()
        self.entry_usuario_registro = tk.Entry(self.frame_registro, font=('Arial', 12), width=20)
        self.entry_usuario_registro.pack(pady=5)
        tk.Label(self.frame_registro, text="Contraseña:", bg='#F5F5F5', fg='#004D40').pack()
        self.entry_contrasena_registro = tk.Entry(self.frame_registro, font=('Arial', 12), width=20, show='*')
        self.entry_contrasena_registro.pack(pady=5)
        registrar_btn = tk.Button(self.frame_registro, text="Registrar", command=self.registrarse, bg='#2196F3', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        registrar_btn.pack(pady=15)
        registrar_btn.bind("<Enter>", lambda e: self.animate_button(registrar_btn, 'enter'))
        registrar_btn.bind("<Leave>", lambda e: self.animate_button(registrar_btn, 'leave'))
        volver_btn = tk.Button(self.frame_registro, text="Volver", command=self.mostrar_inicial, bg='#9E9E9E', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        volver_btn.pack()
        volver_btn.bind("<Enter>", lambda e: self.animate_button(volver_btn, 'enter'))
        volver_btn.bind("<Leave>", lambda e: self.animate_button(volver_btn, 'leave'))
        
        # Frame dedicado para recuperar contraseña
        self.frame_recuperar = tk.Frame(root, bg='#F5F5F5', padx=20, pady=20)
        tk.Label(self.frame_recuperar, text="Recuperar Contraseña", font=('Arial', 16, 'bold'), bg='#F5F5F5', fg='#00695C').pack(pady=10)
        tk.Label(self.frame_recuperar, text="Nombre de Usuario:", bg='#F5F5F5', fg='#004D40').pack()
        self.entry_usuario_recuperar = tk.Entry(self.frame_recuperar, font=('Arial', 12), width=20)
        self.entry_usuario_recuperar.pack(pady=5)
        tk.Label(self.frame_recuperar, text="Nueva Contraseña:", bg='#F5F5F5', fg='#004D40').pack()
        self.entry_nueva_contrasena = tk.Entry(self.frame_recuperar, font=('Arial', 12), width=20, show='*')
        self.entry_nueva_contrasena.pack(pady=5)
        recuperar_btn = tk.Button(self.frame_recuperar, text="Cambiar", command=self.cambiar_contrasena, bg='#FF9800', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        recuperar_btn.pack(pady=15)
        recuperar_btn.bind("<Enter>", lambda e: self.animate_button(recuperar_btn, 'enter'))
        recuperar_btn.bind("<Leave>", lambda e: self.animate_button(recuperar_btn, 'leave'))
        volver_btn = tk.Button(self.frame_recuperar, text="Volver", command=self.mostrar_inicial, bg='#9E9E9E', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        volver_btn.pack()
        volver_btn.bind("<Enter>", lambda e: self.animate_button(volver_btn, 'enter'))
        volver_btn.bind("<Leave>", lambda e: self.animate_button(volver_btn, 'leave'))
        
        # Frame principal (oculto hasta login) - Colorido e interactivo
        self.frame_principal = tk.Frame(root, bg='#F5F5F5')  # Fondo fijo
        
        # Menú superior interactivo
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Agregar PDF", command=self.mostrar_agregar_pdf)
        file_menu.add_command(label="Ver Todos", command=self.ver_pdfs)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=root.quit)
        
        
       # Añadir logo en la parte superior derecha
        try:
            img_path = os.path.join(base_path, "logo.png")
            img = Image.open(img_path)
            img = img.resize((200, 100), Image.Resampling.LANCZOS)
            self.logo_image = ImageTk.PhotoImage(img)
            self.logo_label = tk.Label(self.frame_principal, image=self.logo_image, bg='#F5F5F5')
            self.logo_label.place(relx=0.9, rely=0.05, anchor="ne")
        except FileNotFoundError:
                messagebox.showwarning("Advertencia", "Imagen del logo no encontrada. Actualiza 'ruta_a_tu_imagen.png' en el código.", parent=self.root)
        
        # Barra de búsqueda
        search_frame = tk.Frame(self.frame_principal, bg='#F5F5F5')
        search_frame.pack(pady=10)
        tk.Label(search_frame, text="Buscar:", bg='#F5F5F5', fg='#004D40').pack(side='left', padx=5)
        self.entry_busqueda = tk.Entry(search_frame, font=('Arial', 12), width=30)
        self.entry_busqueda.pack(side='left', padx=5)
        buscar_btn = tk.Button(search_frame, text="Buscar", command=self.buscar_pdfs, bg='#2196F3', fg='white', font=('Arial', 12, 'bold'), padx=20, pady=10)
        buscar_btn.pack(side='left', padx=5)
        buscar_btn.bind("<Enter>", lambda e: self.animate_button(buscar_btn, 'enter'))
        buscar_btn.bind("<Leave>", lambda e: self.animate_button(buscar_btn, 'leave'))
        
        # Botones coloridos e interactivos
        btn_frame = tk.Frame(self.frame_principal, bg='#F5F5F5')
        btn_frame.pack(pady=10)
        agregar_btn = tk.Button(btn_frame, text="➕ Agregar PDF", command=self.mostrar_agregar_pdf, bg='#4CAF50', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10, relief='raised')
        agregar_btn.pack(side='left', padx=5)
        agregar_btn.bind("<Enter>", lambda e: self.animate_button(agregar_btn, 'enter'))
        agregar_btn.bind("<Leave>", lambda e: self.animate_button(agregar_btn, 'leave'))
        ver_btn = tk.Button(btn_frame, text="👁️ Ver PDFs", command=self.ver_pdfs, bg='#2196F3', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10, relief='raised')
        ver_btn.pack(side='left', padx=5)
        ver_btn.bind("<Enter>", lambda e: self.animate_button(ver_btn, 'enter'))
        ver_btn.bind("<Leave>", lambda e: self.animate_button(ver_btn, 'leave'))
        eliminar_btn = tk.Button(btn_frame, text="🗑️ Eliminar PDF", command=self.eliminar_pdf, bg='#F44336', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10, relief='raised')
        eliminar_btn.pack(side='left', padx=5)
        eliminar_btn.bind("<Enter>", lambda e: self.animate_button(eliminar_btn, 'enter'))
        eliminar_btn.bind("<Leave>", lambda e: self.animate_button(eliminar_btn, 'leave'))
        detalles_btn = tk.Button(btn_frame, text="🔍 Detalles", command=self.mostrar_detalles_pdf, bg='#FF9800', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10, relief='raised')
        detalles_btn.pack(side='left', padx=5)
        detalles_btn.bind("<Enter>", lambda e: self.animate_button(detalles_btn, 'enter'))
        detalles_btn.bind("<Leave>", lambda e: self.animate_button(detalles_btn, 'leave'))
        
        # Treeview para lista (actualizado con columnas para cédula y nombres)
        tree_frame = tk.Frame(self.frame_principal, bg='#F5F5F5')
        tree_frame.pack(pady=10, fill='both', expand=True)
        self.tree = ttk.Treeview(tree_frame, columns=("ID", "Nombre", "Descripción", "Tamaño", "Fecha", "Cédula", "Nombres"), show="headings", height=15)
        self.tree.heading("ID", text="ID")
        self.tree.heading("Nombre", text="Nombre del PDF")
        self.tree.heading("Descripción", text="Descripción")
        self.tree.heading("Tamaño", text="Tamaño (bytes)")
        self.tree.heading("Fecha", text="Fecha Subida")
        self.tree.heading("Cédula", text="Cédula Asociada")
        self.tree.heading("Nombres", text="Nombres Asociados")
        self.tree.column("ID", width=50)
        self.tree.column("Nombre", width=150)
        self.tree.column("Descripción", width=200)
        self.tree.column("Tamaño", width=80)
        self.tree.column("Fecha", width=120)
        self.tree.column("Cédula", width=100)
        self.tree.column("Nombres", width=150)
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Evento interactivo: Doble clic para abrir PDF
        self.tree.bind('<Double-1>', self.abrir_pdf)
        
        # Barra de progreso
        self.progress = Progressbar(self.frame_principal, mode='indeterminate')
        
        # Barra de estado
        self.status = tk.Label(self.frame_principal, text="Listo", bg='#F5F5F5', fg='#00695C', relief='sunken', anchor='w')
        self.status.pack(side='bottom', fill='x')
    
    def animate_button(self, button, action):
        if action == 'enter':
            button.config(bg=random_gray_blue(), relief='raised')
        else:
            button.config(bg=button['bg'], relief='raised')
    
    def bounce_button(self, button, command):
        def bounce(step=0, steps=10, direction=1):
            if step < steps:
                scale = 1 + direction * (0.1 * (1 - step / steps))
                button.config(font=("Arial", int(12 * scale)))
                self.root.after(20, bounce, step + 1, direction * -1 if step == steps // 2 else direction)
            else:
                command()
                button.config(font=("Arial", 12))
        bounce()
    
    def slide_in_frame(self, frame, start_relx=1.0, end_relx=0.0, steps=20, callback=None):
        pos = start_relx
        frame.place(relx=pos, rely=0.0, relwidth=1.0, relheight=1.0)
        def animate(step=0):
            if step < steps:
                t = step / steps
                eased = ease_out(t)
                new_relx = start_relx - eased * (start_relx - end_relx)
                frame.place(relx=new_relx, rely=0.0, relwidth=1.0, relheight=1.0)
                self.root.after(20, animate, step + 1)
            else:
                if callback:
                    callback()  # Ejecutar el callback al finalizar la animación
        animate()
    
    def fade_in_window(self, window, start_scale=0.8, end_scale=1.0, steps=10):
        scale = start_scale
        if sys.platform in ['win32', 'darwin']:
            window.attributes('-alpha', scale)
        else:
            window.configure(bg=f'#{int(255*scale):02x}{int(255*scale):02x}{int(255*scale):02x}')
        def animate(step=0):
            if step < steps:
                t = step / steps
                eased = ease_out(t)
                new_scale = start_scale + eased * (end_scale - start_scale)
                if sys.platform in ['win32', 'darwin']:
                    window.attributes('-alpha', new_scale)
                else:
                    window.configure(bg=f'#{int(255*new_scale):02x}{int(255*new_scale):02x}{int(255*new_scale):02x}')
                self.root.after(50, animate, step + 1)
        animate()
    
    def animate_access_text(self):
        self.access_scale += 0.02 if self.access_scale < 1.2 else -0.02
        if self.access_scale > 1.2 or self.access_scale < 1.0:
            self.access_scale = 1.2 if self.access_scale < 1.0 else 1.0
        try:
            self.access_text.config(font=('Old English Text MT', int(20 * self.access_scale), 'bold'))
        except:
            self.access_text.config(font=('Times New Roman', int(20 * self.access_scale), 'bold'))
        self.root.after(50, self.animate_access_text)
    
    def fade_in_text(self, label):
        if self.intro_alpha < 1.0:
            self.intro_alpha += 0.05
            if sys.platform in ['win32', 'darwin']:
                label.config(bg=f'#2c2434', fg=f'#{int(255*self.intro_alpha):02x}{int(255*self.intro_alpha):02x}{int(255*self.intro_alpha):02x}')
            else:
                label.config(fg=f'#{int(255*self.intro_alpha):02x}{int(255*self.intro_alpha):02x}{int(255*self.intro_alpha):02x}')
            self.root.after(50, lambda: self.fade_in_text(label))
    
    def fade_background(self):
        if self.current_color_index < len(self.colors) - 1:
            self.current_color_index += 1
        else:
            self.current_color_index = 0
        self.frame_intro.config(bg=self.colors[self.current_color_index])
        self.root.after(1000, self.fade_background)
    
    def on_intro_click(self, event):
        self.frame_intro.pack_forget()
        self.mostrar_inicial()
    
    def mostrar_inicial(self):
        # Ocultar todos los frames antes de la transición
        self.frame_login.pack_forget()
        self.frame_registro.pack_forget()
        self.frame_recuperar.pack_forget()
        self.frame_principal.pack_forget()
        self.root.update()
        # Mostrar frame_inicial con animación y callback para aplicar pack
        self.slide_in_frame(self.frame_inicial, callback=lambda: self.frame_inicial.pack(expand=True, fill='both'))

    def mostrar_login(self):
        self.frame_inicial.pack_forget()
        self.frame_registro.pack_forget()
        self.frame_recuperar.pack_forget()
        self.frame_principal.pack_forget()
        self.root.update()
        self.slide_in_frame(self.frame_login, callback=lambda: self.frame_login.pack(expand=True, fill='both'))

    def mostrar_registro(self):
        self.frame_inicial.pack_forget()
        self.frame_login.pack_forget()
        self.frame_recuperar.pack_forget()
        self.frame_principal.pack_forget()
        self.root.update()
        self.slide_in_frame(self.frame_registro, callback=lambda: self.frame_registro.pack(expand=True, fill='both'))

    def mostrar_recuperar(self):
        self.frame_inicial.pack_forget()
        self.frame_login.pack_forget()
        self.frame_registro.pack_forget()
        self.frame_principal.pack_forget()
        self.root.update()
        self.slide_in_frame(self.frame_recuperar, callback=lambda: self.frame_recuperar.pack(expand=True, fill='both'))
    
    def registrarse(self):
        nombre = self.entry_usuario_registro.get().strip()
        contrasena = self.entry_contrasena_registro.get().strip()
        if not nombre or not contrasena:
            messagebox.showerror("Error", "Ingresa nombre de usuario y contraseña", parent=self.root)
            return
        try:
            hash_pass = hash_contrasena(contrasena)
            self.cursor.execute("INSERT INTO Usuarios (nombre, contrasena) VALUES (?, ?)", (nombre, hash_pass))
            self.conn.commit()
            messagebox.showinfo("Éxito", f"Usuario '{nombre}' registrado correctamente", parent=self.root)
            self.mostrar_login()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "El usuario ya existe", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)
    
    def login(self):
        nombre = self.entry_usuario_login.get().strip()
        contrasena = self.entry_contrasena_login.get().strip()
        if not nombre or not contrasena:
            messagebox.showerror("Error", "Ingresa nombre de usuario y contraseña", parent=self.root)
            return
        try:
            self.cursor.execute("SELECT id, contrasena FROM Usuarios WHERE nombre = ?", (nombre,))
            result = self.cursor.fetchone()
            if result:
                usuario_id, hash_stored = result
                if hash_contrasena(contrasena) == hash_stored:
                    self.usuario_actual = usuario_id
                    self.frame_login.pack_forget()
                    self.frame_principal.pack(expand=True, fill='both')
                    self.status.config(text=f"Bienvenido, {nombre}! Usa los botones o menú para interactuar.")
                    messagebox.showinfo("Éxito", f"Sesión iniciada como {nombre}", parent=self.root)
                else:
                    messagebox.showerror("Error", "Contraseña incorrecta", parent=self.root)
            else:
                messagebox.showerror("Error", "Usuario no encontrado", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)
    
    def cambiar_contrasena(self):
        nombre = self.entry_usuario_recuperar.get().strip()
        nueva_contrasena = self.entry_nueva_contrasena.get().strip()
        if not nombre or not nueva_contrasena:
            messagebox.showerror("Error", "Ingresa nombre de usuario y nueva contraseña", parent=self.root)
            return
        try:
            self.cursor.execute("SELECT id FROM Usuarios WHERE nombre = ?", (nombre,))
            result = self.cursor.fetchone()
            if result:
                hash_new = hash_contrasena(nueva_contrasena)
                self.cursor.execute("UPDATE Usuarios SET contrasena = ? WHERE nombre = ?", (hash_new, nombre))
                self.conn.commit()
                messagebox.showinfo("Éxito", "Contraseña actualizada correctamente", parent=self.root)
                self.mostrar_inicial()
            else:
                messagebox.showerror("Error", "Usuario no encontrado", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)
    
    def mostrar_agregar_pdf(self):
        add_window = Toplevel(self.root)
        add_window.title("Agregar PDF")
        add_window.geometry("500x400")
        add_window.configure(bg='#F5F5F5')
        self.fade_in_window(add_window)
        
        tk.Label(add_window, text="Agregar Nuevo PDF", font=('Arial', 14, 'bold'), bg='#F5F5F5', fg='#00695C').pack(pady=15)
        
        self.selected_file = None
        btn_buskar = tk.Button(add_window, text="Buscar Archivo PDF", command=self.seleccionar_archivo, bg='#4CAF50', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        btn_buskar.pack(pady=15)
        btn_buskar.bind("<Enter>", lambda e: self.animate_button(btn_buskar, 'enter'))
        btn_buskar.bind("<Leave>", lambda e: self.animate_button(btn_buskar, 'leave'))
        
        self.label_file = tk.Label(add_window, text="Ningún archivo seleccionado", bg='#F5F5F5', fg='#004D40')
        self.label_file.pack(pady=10)
        
        self.entry_descripcion = tk.Entry(add_window, font=('Arial', 12), width=40)
        tk.Label(add_window, text="Descripción:", bg='#F5F5F5', fg='#004D40').pack()
        self.entry_descripcion.pack(pady=10)
        
        self.entry_cedula = tk.Entry(add_window, font=('Arial', 12), width=40)
        tk.Label(add_window, text="Cédula:", bg='#F5F5F5', fg='#004D40').pack()
        self.entry_cedula.pack(pady=10)
        
        self.entry_nombres = tk.Entry(add_window, font=('Arial', 12), width=40)
        tk.Label(add_window, text="Nombres:", bg='#F5F5F5', fg='#004D40').pack()
        self.entry_nombres.pack(pady=10)
        
        self.entry_etiquetas = tk.Entry(add_window, font=('Arial', 12), width=40)
        tk.Label(add_window, text="Etiquetas (separadas por coma):", bg='#F5F5F5', fg='#004D40').pack()
        self.entry_etiquetas.pack(pady=10)
        
        btn_agregar = tk.Button(add_window, text="Agregar", command=lambda: self.procesar_agregar_pdf(add_window), bg='#2196F3', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        btn_agregar.pack(pady=15)
        btn_agregar.bind("<Enter>", lambda e: self.animate_button(btn_agregar, 'enter'))
        btn_agregar.bind("<Leave>", lambda e: self.animate_button(btn_agregar, 'leave'))
    
    def seleccionar_archivo(self):
        self.selected_file = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if self.selected_file:
            self.label_file.config(text=os.path.basename(self.selected_file))
    
    def procesar_agregar_pdf(self, window):
        if not self.selected_file:
            messagebox.showerror("Error", "Selecciona un archivo PDF", parent=window)
            return
        descripcion = self.entry_descripcion.get().strip()
        cedula = self.entry_cedula.get().strip()
        nombres = self.entry_nombres.get().strip()
        etiquetas_str = self.entry_etiquetas.get().strip()
        
        if not cedula or not nombres:
            messagebox.showerror("Error", "Cédula y nombres son requeridos", parent=window)
            return
        
        self.progress.pack(pady=5)
        self.progress.start()
        self.root.update()
        try:
            with open(self.selected_file, 'rb') as f:
                datos = f.read()
            tamano = len(datos)
            nombre = os.path.basename(self.selected_file)
            
            self.cursor.execute("SELECT id FROM Personas WHERE cedula = ?", (cedula,))
            result = self.cursor.fetchone()
            if result:
                persona_id = result[0]
                self.cursor.execute("UPDATE Personas SET nombres = ? WHERE id = ?", (nombres, persona_id))
            else:
                self.cursor.execute("INSERT INTO Personas (cedula, nombres) VALUES (?, ?)", (cedula, nombres))
                persona_id = self.cursor.lastrowid
            
            self.cursor.execute('''
                INSERT INTO PDFs (nombre, descripcion, datos, tamano, fecha_subida, usuario_id, persona_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (nombre, descripcion, datos, tamano, datetime.now().isoformat(), self.usuario_actual, persona_id))
            pdf_id = self.cursor.lastrowid
            
            if etiquetas_str:
                for etiqueta in [e.strip() for e in etiquetas_str.split(',') if e.strip()]:
                    self.cursor.execute("INSERT OR IGNORE INTO Etiquetas (nombre) VALUES (?)", (etiqueta,))
                    self.cursor.execute("SELECT id FROM Etiquetas WHERE nombre = ?", (etiqueta,))
                    etiqueta_id = self.cursor.fetchone()[0]
                    self.cursor.execute("INSERT OR IGNORE INTO PDF_Etiquetas (pdf_id, etiqueta_id) VALUES (?, ?)", (pdf_id, etiqueta_id))
            
            self.cursor.execute('''
                INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha)
                VALUES (?, ?, ?, ?)
            ''', ("Agregar PDF", pdf_id, self.usuario_actual, datetime.now().isoformat()))
            
            self.conn.commit()
            self.status.config(text=f"PDF '{nombre}' agregado exitosamente (ID: {pdf_id}, Asociado a Cédula: {cedula})")
            messagebox.showinfo("Éxito", f"PDF agregado: {nombre}", parent=self.root)
            window.destroy()
            self.ver_pdfs()
            self.animate_treeview_insert(pdf_id)  # Animación al registrar datos
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", str(e), parent=self.root)
            self.status.config(text="Error al agregar PDF")
        finally:
            self.progress.stop()
            self.progress.pack_forget()
    
    def animate_treeview_insert(self, pdf_id):
        # Animación al insertar en Treeview (parpadeo o cambio de color)
        self.root.after(100, lambda: self.tree.config(background=random_gray_blue()))
        self.root.after(500, lambda: self.tree.config(background='#F5F5F5'))
    
    def buscar_pdfs(self):
        term = self.entry_busqueda.get().strip()
        if not term:
            self.ver_pdfs()
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            self.cursor.execute('''
                SELECT p.id, p.nombre, p.descripcion, p.tamano, p.fecha_subida, pe.cedula, pe.nombres 
                FROM PDFs p 
                LEFT JOIN Personas pe ON p.persona_id = pe.id 
                WHERE p.usuario_id = ? AND (p.nombre LIKE ? OR p.descripcion LIKE ? OR pe.cedula LIKE ? OR pe.nombres LIKE ?)
            ''', (self.usuario_actual, f'%{term}%', f'%{term}%', f'%{term}%', f'%{term}%'))
            rows = self.cursor.fetchall()
            for row in rows:
                self.tree.insert("", "end", values=row)
            self.status.config(text=f"Se muestran {len(rows)} resultados de búsqueda")
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)
    
    def mostrar_detalles_pdf(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Advertencia", "Selecciona un PDF de la lista", parent=self.root)
            return
        values = self.tree.item(selected[0])['values']
        pdf_id, pdf_nombre, descripcion, tamano, fecha, cedula, nombres = values
        
        details_window = Toplevel(self.root)
        details_window.title("Detalles del PDF")
        details_window.geometry("400x300")
        details_window.configure(bg='#F5F5F5')
        self.fade_in_window(details_window)
        
        tk.Label(details_window, text=f"ID: {pdf_id}", bg='#F5F5F5', fg='#004D40').pack(pady=5)
        tk.Label(details_window, text=f"Nombre: {pdf_nombre}", bg='#F5F5F5', fg='#004D40').pack(pady=5)
        tk.Label(details_window, text=f"Descripción: {descripcion}", bg='#F5F5F5', fg='#004D40').pack(pady=5)
        tk.Label(details_window, text=f"Tamaño: {tamano} bytes", bg='#F5F5F5', fg='#004D40').pack(pady=5)
        tk.Label(details_window, text=f"Fecha: {fecha}", bg='#F5F5F5', fg='#004D40').pack(pady=5)
        tk.Label(details_window, text=f"Cédula: {cedula}", bg='#F5F5F5', fg='#004D40').pack(pady=5)
        tk.Label(details_window, text=f"Nombres: {nombres}", bg='#F5F5F5', fg='#004D40').pack(pady=5)
        
        btn_abrir = tk.Button(details_window, text="Abrir PDF", command=lambda: self.abrir_pdf_id(pdf_id, details_window), bg='#2196F3', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        btn_abrir.pack(pady=5)
        btn_abrir.bind("<Enter>", lambda e: self.animate_button(btn_abrir, 'enter'))
        btn_abrir.bind("<Leave>", lambda e: self.animate_button(btn_abrir, 'leave'))
        
        btn_modificar = tk.Button(details_window, text="Modificar Datos", command=lambda: self.modificar_pdf(pdf_id, descripcion, cedula, nombres, details_window), bg='#FF9800', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        btn_modificar.pack(pady=5)
        btn_modificar.bind("<Enter>", lambda e: self.animate_button(btn_modificar, 'enter'))
        btn_modificar.bind("<Leave>", lambda e: self.animate_button(btn_modificar, 'leave'))
        
        btn_eliminar = tk.Button(details_window, text="Eliminar", command=lambda: self.eliminar_pdf_id(pdf_id, details_window), bg='#F44336', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        btn_eliminar.pack(pady=5)
        btn_eliminar.bind("<Enter>", lambda e: self.animate_button(btn_eliminar, 'enter'))
        btn_eliminar.bind("<Leave>", lambda e: self.animate_button(btn_eliminar, 'leave'))
    
    def abrir_pdf_id(self, pdf_id, window=None):
        try:
            self.cursor.execute("SELECT datos, nombre FROM PDFs WHERE id = ? AND usuario_id = ?", (pdf_id, self.usuario_actual))
            result = self.cursor.fetchone()
            if result:
                datos, nombre = result
                temp_file = os.path.join(tempfile.gettempdir(), f"temp_{nombre}")
                with open(temp_file, 'wb') as f:
                    f.write(datos)
                os.startfile(temp_file) if os.name == 'nt' else webbrowser.open(temp_file)
                self.status.config(text=f"Abriendo PDF: {nombre}")
                if window:
                    window.destroy()
            else:
                messagebox.showerror("Error", "PDF no encontrado", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el PDF: {e}", parent=self.root)
    
    def modificar_pdf(self, pdf_id, current_descripcion, current_cedula, current_nombres, window):
        mod_window = Toplevel(self.root)
        mod_window.title("Modificar PDF")
        mod_window.geometry("400x300")
        mod_window.configure(bg='#F5F5F5')
        self.fade_in_window(mod_window)
        
        tk.Label(mod_window, text="Modificar Datos", font=('Arial', 14, 'bold'), bg='#F5F5F5', fg='#00695C').pack(pady=10)
        
        self.entry_mod_descripcion = tk.Entry(mod_window, font=('Arial', 12), width=30)
        tk.Label(mod_window, text="Descripción:", bg='#F5F5F5', fg='#004D40').pack()
        self.entry_mod_descripcion.insert(0, current_descripcion)
        self.entry_mod_descripcion.pack(pady=5)
        
        self.entry_mod_cedula = tk.Entry(mod_window, font=('Arial', 12), width=30)
        tk.Label(mod_window, text="Cédula:", bg='#F5F5F5', fg='#004D40').pack()
        self.entry_mod_cedula.insert(0, current_cedula)
        self.entry_mod_cedula.pack(pady=5)
        
        self.entry_mod_nombres = tk.Entry(mod_window, font=('Arial', 12), width=30)
        tk.Label(mod_window, text="Nombres:", bg='#F5F5F5', fg='#004D40').pack()
        self.entry_mod_nombres.insert(0, current_nombres)
        self.entry_mod_nombres.pack(pady=5)
        
        self.entry_mod_etiquetas = tk.Entry(mod_window, font=('Arial', 12), width=30)
        tk.Label(mod_window, text="Etiquetas (separadas por coma):", bg='#F5F5F5', fg='#004D40').pack()
        self.cursor.execute("SELECT e.nombre FROM Etiquetas e JOIN PDF_Etiquetas pe ON e.id = pe.etiqueta_id WHERE pe.pdf_id = ?", (pdf_id,))
        etiquetas_actuales = ', '.join([row[0] for row in self.cursor.fetchall()])
        self.entry_mod_etiquetas.insert(0, etiquetas_actuales)
        self.entry_mod_etiquetas.pack(pady=5)
        
        btn_guardar = tk.Button(mod_window, text="Guardar Cambios", command=lambda: self.guardar_modificaciones(pdf_id, window, mod_window), bg='#4CAF50', fg='white', font=('Arial', 12, 'bold'), padx=30, pady=10)
        btn_guardar.pack(pady=10)
        btn_guardar.bind("<Enter>", lambda e: self.animate_button(btn_guardar, 'enter'))
        btn_guardar.bind("<Leave>", lambda e: self.animate_button(btn_guardar, 'leave'))
    
    def guardar_modificaciones(self, pdf_id, details_window, mod_window):
        descripcion = self.entry_mod_descripcion.get().strip()
        cedula = self.entry_mod_cedula.get().strip()
        nombres = self.entry_mod_nombres.get().strip()
        etiquetas_str = self.entry_mod_etiquetas.get().strip()
        
        try:
            self.cursor.execute("UPDATE PDFs SET descripcion = ? WHERE id = ?", (descripcion, pdf_id))
            
            self.cursor.execute("SELECT persona_id FROM PDFs WHERE id = ?", (pdf_id,))
            persona_id = self.cursor.fetchone()[0]
            if persona_id:
                self.cursor.execute("UPDATE Personas SET cedula = ?, nombres = ? WHERE id = ?", (cedula, nombres, persona_id))
            else:
                self.cursor.execute("INSERT INTO Personas (cedula, nombres) VALUES (?, ?)", (cedula, nombres))
                persona_id = self.cursor.lastrowid
                self.cursor.execute("UPDATE PDFs SET persona_id = ? WHERE id = ?", (persona_id, pdf_id))
            
            self.cursor.execute("DELETE FROM PDF_Etiquetas WHERE pdf_id = ?", (pdf_id,))
            if etiquetas_str:
                for etiqueta in [e.strip() for e in etiquetas_str.split(',') if e.strip()]:
                    self.cursor.execute("INSERT OR IGNORE INTO Etiquetas (nombre) VALUES (?)", (etiqueta,))
                    self.cursor.execute("SELECT id FROM Etiquetas WHERE nombre = ?", (etiqueta,))
                    etiqueta_id = self.cursor.fetchone()[0]
                    self.cursor.execute("INSERT OR IGNORE INTO PDF_Etiquetas (pdf_id, etiqueta_id) VALUES (?, ?)", (pdf_id, etiqueta_id))
            
            self.conn.commit()
            messagebox.showinfo("Éxito", "Datos modificados correctamente", parent=mod_window)
            mod_window.destroy()
            details_window.destroy()
            self.ver_pdfs()
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", str(e), parent=mod_window)
    
    def eliminar_pdf_id(self, pdf_id, window):
        if not pdf_id or not isinstance(pdf_id, (int, str)):
            messagebox.showerror("Error", "ID de PDF inválido", parent=window)
            return
        if not self.usuario_actual:
            messagebox.showerror("Error", "No hay usuario autenticado", parent=window)
            return
        try:
            pdf_id = int(pdf_id)
            self.cursor.execute("DELETE FROM PDFs WHERE id = ? AND usuario_id = ?", (pdf_id, self.usuario_actual))
            if self.cursor.rowcount == 0:
                messagebox.showerror("Error", "PDF no encontrado o no autorizado para eliminar", parent=window)
                return
            self.cursor.execute('''
                INSERT INTO Auditoria (accion, pdf_id, usuario_id, fecha)
                VALUES (?, ?, ?, ?)
            ''', ("Eliminar PDF", pdf_id, self.usuario_actual, datetime.now().isoformat()))
            self.conn.commit()
            self.status.config(text=f"PDF ID {pdf_id} eliminado")
            messagebox.showinfo("Éxito", "PDF eliminado correctamente", parent=window)
            window.destroy()
            self.ver_pdfs()
        except sqlite3.IntegrityError as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error de integridad: {e}. Puede haber dependencias.", parent=window)
        except sqlite3.Error as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error en la base de datos: {e}", parent=self.root)
        except ValueError as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"ID inválido: {e}", parent=window)
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Error inesperado: {e}", parent=window)

    def ver_pdfs(self):
        if not self.usuario_actual:
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            self.cursor.execute('''
                SELECT p.id, p.nombre, p.descripcion, p.tamano, p.fecha_subida, pe.cedula, pe.nombres 
                FROM PDFs p 
                LEFT JOIN Personas pe ON p.persona_id = pe.id 
                WHERE p.usuario_id = ?
            ''', (self.usuario_actual,))
            rows = self.cursor.fetchall()
            for row in rows:
                item = self.tree.insert("", "end", values=row)
                self.animate_tree_row(item)
            self.status.config(text=f"Se muestran {len(rows)} PDFs")
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.root)
    
    def animate_tree_row(self, item):
        if not self.animating and item:
            self.animating = True
            self.tree.tag_configure("highlight", background='lightblue')
            self.tree.item(item, tags=("highlight",))
            self.root.after(500, lambda: [self.tree.item(item, tags=()) if item in self.tree.get_children() else None, setattr(self, 'animating', False)])
    
    def eliminar_pdf(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Advertencia", "Selecciona un PDF de la lista", parent=self.root)
            return
        pdf_id = self.tree.item(selected[0])['values'][0]
        self.eliminar_pdf_id(pdf_id, self.root)
    
    def abrir_pdf(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        pdf_id = self.tree.item(selected[0])['values'][0]
        self.abrir_pdf_id(pdf_id)

if __name__ == "__main__":
    root = tk.Tk()
    app = AppDBPDF(root)
    root.mainloop()





                                 #  ______-_______ ALPHA V1.0 - LAUNCH TEST ____-___ #