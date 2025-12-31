import customtkinter as ctk
from tkinter import filedialog
from PIL import Image
import os
import sys
import ctypes
from .controller import AppController

# --- BRAND COLORS ---
COLLEXA_RED = "#D32F2F"    
COLLEXA_DARK_BG = "#1a1a1a"
COLLEXA_LIGHT_BG = "#F0F0F0"

class CollexaView(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.controller = AppController(self.log)

        try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('collexa.netdeploy.1.0')
        except: pass

        self.title("Collexa NetDeploy") 
        self.geometry("850x750")
        
        self._load_icon()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self._build_ui()
        self._load_creds()
        
        # Default Theme
        self.change_theme("Dark")

    def _get_asset(self, name):
        if getattr(sys, 'frozen', False): base = sys._MEIPASS
        else: base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, "assets", name)

    def _load_icon(self):
        try:
            icon = self._get_asset("app_icon.ico")
            if os.path.exists(icon): self.iconbitmap(default=icon)
        except: pass

    def _create_dark_mode_logo(self, img_path):
        """Converts black pixels to white for dark mode."""
        img = Image.open(img_path).convert("RGBA")
        datas = img.getdata()
        new_data = []
        for item in datas:
            # If pixel is dark (Black/Grey), turn White
            if item[0] < 80 and item[1] < 80 and item[2] < 80:
                new_data.append((255, 255, 255, item[3]))
            else:
                new_data.append(item)
        img.putdata(new_data)
        return img

    def _build_ui(self):
        self.main_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.main_panel.grid(row=0, column=0, sticky="nsew", padx=20, pady=10)
        self.main_panel.grid_columnconfigure(0, weight=1)
        self.main_panel.grid_rowconfigure(5, weight=1)

        # === HEADER ===
        header_box = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        header_box.grid(row=0, column=0, sticky="ew", pady=(0,10))

        try:
            img_path = self._get_asset("header_logo.png")
            if os.path.exists(img_path):
                light_mode_img = Image.open(img_path)
                dark_mode_img = self._create_dark_mode_logo(img_path)
                ratio = 60 / light_mode_img.height
                new_size = (int(light_mode_img.width * ratio), 60)
                
                img = ctk.CTkImage(light_image=light_mode_img, dark_image=dark_mode_img, size=new_size)
                ctk.CTkLabel(header_box, image=img, text="").pack()
            else:
                ctk.CTkLabel(header_box, text="COLLEXA", font=("Arial", 36, "bold"), text_color=COLLEXA_RED).pack()
        except: pass

        powered_frame = ctk.CTkFrame(header_box, fg_color="transparent")
        powered_frame.pack(pady=(5, 0))
        self.lbl_powered = ctk.CTkLabel(powered_frame, text="POWERED BY ", font=("Arial", 12, "bold"))
        self.lbl_powered.pack(side="left")
        ctk.CTkLabel(powered_frame, text="COLLEXA", font=("Arial", 12, "bold"), text_color=COLLEXA_RED).pack(side="left")

        # === 1. OPERATION MODE ===
        files_frame = ctk.CTkFrame(self.main_panel, border_color="gray", border_width=2)
        files_frame.grid(row=1, column=0, sticky="ew", pady=5)
        files_frame.grid_columnconfigure(1, weight=1)

        self.lbl_grp1 = ctk.CTkLabel(files_frame, text=" Operation Mode & Files ")
        self.lbl_grp1.place(x=15, y=-8)

        ctk.CTkLabel(files_frame, text="Operation Mode:").grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.mode_var = ctk.StringVar(value="Configuration Push")
        self.mode_combo = ctk.CTkComboBox(files_frame, values=["Configuration Push", "Retrieve Data (Show)"], 
                                          command=self.update_ui_state, variable=self.mode_var, width=250,
                                          button_color=COLLEXA_RED, border_color=COLLEXA_RED)
        self.mode_combo.grid(row=0, column=1, padx=10, pady=(20, 5), sticky="w")

        ctk.CTkLabel(files_frame, text="Target List (Excel)").grid(row=1, column=0, padx=20, pady=5, sticky="w")
        self.entry_excel = ctk.CTkEntry(files_frame)
        self.entry_excel.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        ctk.CTkButton(files_frame, text="Browse", width=80, fg_color=COLLEXA_RED, hover_color="#B71C1C", 
                      command=lambda: self.browse_file(self.entry_excel)).grid(row=1, column=2, padx=10)

        # -- Dynamic Widgets --
        self.lbl_tmpl = ctk.CTkLabel(files_frame, text="Jinja2 Template")
        self.entry_template = ctk.CTkEntry(files_frame)
        self.btn_tmpl = ctk.CTkButton(files_frame, text="Browse", width=80, fg_color=COLLEXA_RED, command=lambda: self.browse_file(self.entry_template))
        
        self.lbl_cmd = ctk.CTkLabel(files_frame, text="Command to Run")
        self.entry_cmd = ctk.CTkEntry(files_frame, placeholder_text="e.g. show version")

        self.lbl_nc = ctk.CTkLabel(files_frame, text="Filter (XML/JSON)")
        self.entry_nc = ctk.CTkEntry(files_frame, placeholder_text="Path to .xml or .json filter")
        self.btn_nc = ctk.CTkButton(files_frame, text="Browse", width=80, fg_color=COLLEXA_RED, command=lambda: self.browse_file(self.entry_nc))
        
        self.format_frame = ctk.CTkFrame(files_frame, fg_color="transparent")
        self.format_var = ctk.StringVar(value="JSON")
        ctk.CTkLabel(self.format_frame, text="Save As:").pack(side="left", padx=(0,10))
        for fmt in ["JSON", "XML", "Text"]:
            ctk.CTkRadioButton(self.format_frame, text=fmt, variable=self.format_var, value=fmt, 
                               fg_color=COLLEXA_RED, hover_color=COLLEXA_RED, command=self.update_ui_state).pack(side="left", padx=5)
        
        self.convert_var = ctk.BooleanVar(value=True)
        self.chk_convert = ctk.CTkCheckBox(self.format_frame, text="Auto-Convert to Excel", variable=self.convert_var,
                                           fg_color=COLLEXA_RED, hover_color=COLLEXA_RED)
        self.chk_convert.pack(side="left", padx=20)

        self.regex_frame = ctk.CTkFrame(files_frame, fg_color="transparent")
        ctk.CTkLabel(self.regex_frame, text="Regex Excel").pack(side="left")
        self.entry_regex = ctk.CTkEntry(self.regex_frame)
        self.entry_regex.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(self.regex_frame, text="Browse", width=60, fg_color=COLLEXA_RED, 
                      command=lambda: self.browse_file(self.entry_regex)).pack(side="left")

        # === 2. SETTINGS ===
        settings_grid = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        settings_grid.grid(row=2, column=0, sticky="ew", pady=5)
        settings_grid.grid_columnconfigure(0, weight=1)
        settings_grid.grid_columnconfigure(1, weight=1)

        p_frame = ctk.CTkFrame(settings_grid, border_color="gray", border_width=2)
        p_frame.grid(row=0, column=0, sticky="nsew", padx=(0,5))
        p_frame.grid_columnconfigure(1, weight=1)
        self.lbl_grp2 = ctk.CTkLabel(p_frame, text=" Protocol & Vendor ")
        self.lbl_grp2.place(x=15, y=-8)

        self.protocol_var = ctk.StringVar(value="SSH")
        ctk.CTkRadioButton(p_frame, text="SSH", variable=self.protocol_var, value="SSH", fg_color=COLLEXA_RED, command=self.update_ui_state).grid(row=0, column=0, padx=20, pady=(20,5))
        ctk.CTkRadioButton(p_frame, text="NETCONF", variable=self.protocol_var, value="NETCONF", fg_color=COLLEXA_RED, command=self.update_ui_state).grid(row=1, column=0, padx=20, pady=5)
        self.vendor_combo = ctk.CTkComboBox(p_frame, values=["Cisco IOS", "Cisco XR", "Juniper Junos", "Nokia SR OS", "Huawei VRP"],
                                            button_color=COLLEXA_RED, border_color=COLLEXA_RED)
        self.vendor_combo.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # Credentials & Theme
        c_frame = ctk.CTkFrame(settings_grid, border_color="gray", border_width=2)
        c_frame.grid(row=0, column=1, sticky="nsew", padx=(5,0))
        c_frame.grid_columnconfigure(0, weight=1)
        self.lbl_grp3 = ctk.CTkLabel(c_frame, text=" Credentials & Theme ")
        self.lbl_grp3.place(x=15, y=-8)

        self.entry_user = ctk.CTkEntry(c_frame, placeholder_text="Username")
        self.entry_user.grid(row=0, column=0, padx=20, pady=(20,5), sticky="ew")
        self.entry_pass = ctk.CTkEntry(c_frame, placeholder_text="Password", show="*")
        self.entry_pass.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        self.save_creds_var = ctk.BooleanVar()
        ctk.CTkCheckBox(c_frame, text="Save Creds", variable=self.save_creds_var, fg_color=COLLEXA_RED).grid(row=2, column=0, padx=20, pady=5, sticky="w")
        
        self.seg_theme = ctk.CTkSegmentedButton(c_frame, values=["Light", "Dark"], 
                                                command=self.change_theme,
                                                selected_color=COLLEXA_RED,
                                                selected_hover_color="#B71C1C")
        self.seg_theme.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.seg_theme.set("Dark")

        # === 3. JUMP HOST ===
        j_frame = ctk.CTkFrame(self.main_panel, border_color="gray", border_width=2)
        j_frame.grid(row=3, column=0, sticky="ew", pady=5)
        j_frame.grid_columnconfigure(1, weight=1)
        self.lbl_grp4 = ctk.CTkLabel(j_frame, text=" Jump Host ")
        self.lbl_grp4.place(x=15, y=-8)
        
        self.use_jump = ctk.BooleanVar()
        ctk.CTkCheckBox(j_frame, text="Use Jump Host", variable=self.use_jump, command=self.toggle_jump,
                        fg_color=COLLEXA_RED).grid(row=0, column=0, padx=20, pady=(20,10))
        
        self.jh_host = ctk.CTkEntry(j_frame, placeholder_text="Jump IP"); self.jh_host.grid(row=0, column=1, padx=5)
        self.jh_port = ctk.CTkEntry(j_frame, placeholder_text="22", width=50); self.jh_port.grid(row=0, column=2, padx=5)
        self.jh_user = ctk.CTkEntry(j_frame, placeholder_text="User"); self.jh_user.grid(row=0, column=3, padx=5)
        self.jh_pass = ctk.CTkEntry(j_frame, placeholder_text="Pass", show="*"); self.jh_pass.grid(row=0, column=4, padx=5)
        self.toggle_jump()

        # === 4. ACTION ===
        self.btn_run = ctk.CTkButton(self.main_panel, text="RUN CONFIGURATION", height=45,
                                     font=("Arial", 16, "bold"), fg_color="#008000", hover_color="#006400", 
                                     command=self.on_run) 
        self.btn_run.grid(row=4, column=0, sticky="ew", pady=10)

        # === 5. LOGS ===
        self.log_box = ctk.CTkTextbox(self.main_panel, border_color="gray", border_width=1)
        self.log_box.grid(row=5, column=0, sticky="nsew")

        # INITIAL STATE
        self.update_ui_state()

    # --- HELPERS ---
    def change_theme(self, value):
        ctk.set_appearance_mode(value)
        if value == "Dark":
            bg_color = COLLEXA_DARK_BG
            text_color = "#DCE4EE"
            frame_label_bg = "#2b2b2b"
            power_text = "#D0D0D0"
        else:
            bg_color = COLLEXA_LIGHT_BG
            text_color = "#333333"
            frame_label_bg = "#E0E0E0"
            power_text = "#555555"

        self.configure(fg_color=bg_color)
        for lbl in [self.lbl_grp1, self.lbl_grp2, self.lbl_grp3, self.lbl_grp4]:
            lbl.configure(fg_color=frame_label_bg, text_color=text_color)
        self.lbl_powered.configure(text_color=power_text)

    def update_ui_state(self, event=None):
        mode = self.mode_var.get()
        proto = self.protocol_var.get()

        # Hide all dynamic
        for w in [self.lbl_tmpl, self.entry_template, self.btn_tmpl,
                  self.lbl_cmd, self.entry_cmd,
                  self.lbl_nc, self.entry_nc, self.btn_nc,
                  self.format_frame, self.regex_frame]: w.grid_forget()

        if mode == "Configuration Push":
            self.lbl_tmpl.grid(row=2, column=0, padx=20, pady=5, sticky="w")
            self.entry_template.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
            self.btn_tmpl.grid(row=2, column=2, padx=10, pady=5)
            self.btn_run.configure(text="RUN CONFIGURATION", fg_color="#008000")
        else:
            self.btn_run.configure(text="RETRIEVE DATA", fg_color=COLLEXA_RED)
            self.format_frame.grid(row=3, column=0, columnspan=3, padx=20, pady=5, sticky="w")
            
            if proto == "SSH":
                self.lbl_cmd.grid(row=2, column=0, padx=20, pady=5, sticky="w")
                self.entry_cmd.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
                if self.format_var.get() == "Text": self.regex_frame.grid(row=4, column=0, columnspan=3, padx=20, pady=5, sticky="ew")
            elif proto == "NETCONF":
                self.lbl_nc.grid(row=2, column=0, padx=20, pady=5, sticky="w")
                self.entry_nc.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
                self.btn_nc.grid(row=2, column=2, padx=10, pady=5)

    def toggle_jump(self):
        state = "normal" if self.use_jump.get() else "disabled"
        for w in [self.jh_host, self.jh_port, self.jh_user, self.jh_pass]: w.configure(state=state)

    def browse_file(self, entry):
        f = filedialog.askopenfilename()
        if f: entry.delete(0, "end"); entry.insert(0, f)

    def log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _load_creds(self):
        creds = self.controller.load_creds()
        if creds['main'][0]: self.entry_user.insert(0, creds['main'][0]); self.entry_pass.insert(0, creds['main'][1]); self.save_creds_var.set(True)
        if creds['jump'][0]: self.jh_user.insert(0, creds['jump'][0]); self.jh_pass.insert(0, creds['jump'][1]); self.use_jump.set(True); self.toggle_jump()

    def on_run(self):
        params = {
            'excel': self.entry_excel.get(), 'user': self.entry_user.get(), 'pass': self.entry_pass.get(),
            'protocol': self.protocol_var.get(), 'vendor': self.vendor_combo.get(),
            'use_jump': self.use_jump.get(), 'jh_ip': self.jh_host.get(), 'jh_port': self.jh_port.get() or 22,
            'jh_user': self.jh_user.get(), 'jh_pass': self.jh_pass.get(),
            'mode': 'retrieve' if self.mode_var.get() == "Retrieve Data (Show)" else 'push',
            'cmd': self.entry_cmd.get(), 'template': self.entry_template.get(),
            'netconf_file': self.entry_nc.get(),
            'format': self.format_var.get(), 'auto_convert': self.convert_var.get(),
            'regex_file': self.entry_regex.get()
        }
        
        if self.save_creds_var.get(): self.controller.save_creds('main', params['user'], params['pass'])
        if self.use_jump.get(): self.controller.save_creds('jump', params['jh_user'], params['jh_pass'])
        
        self.btn_run.configure(state="disabled")
        self.controller.run_task(params)
        self.after(2000, lambda: self.btn_run.configure(state="normal"))