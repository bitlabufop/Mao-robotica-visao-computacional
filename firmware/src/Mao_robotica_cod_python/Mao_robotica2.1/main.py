import math
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import mediapipe as mp
from PIL import Image, ImageTk
import serial
import serial.tools.list_ports

# ==========================================================
# CONFIGURAÇÃO DE HARDWARE E LIMITES
# ==========================================================
BAUD_RATE = 115200

# Limite máximo de cada servo (dedo fechado)
ANGULOS_MAX = {
    1: 80,   # Polegar
    2: 130,  # Indicador
    4: 160,  # Médio
    3: 140,  # Anelar
    5: 120   # Mínimo
}

ANGULO_ABERTO = 0
SMOOTH_FACTOR = 0.30


# ==========================================================
# GERENCIADOR SERIAL (ROBUSTO COM LOG E SUPORTE A RECONEXÃO)
# ==========================================================
class ControladorMao:
    def __init__(self, callback_log=None):
        self.serial_conn = None
        self.lock = threading.Lock()
        self.callback_log = callback_log
        self.porta_atual = ""
        self.conectado = False
        self.ultimos_angulos_enviados = {i: -1 for i in ANGULOS_MAX.keys()}
        self.angulos_suavizados = {i: 0.0 for i in ANGULOS_MAX.keys()}

    def conectar(self, porta):
        with self.lock:
            self.desconectar()
            self.porta_atual = porta
            try:
                # dtr=False e rts=False evitam travamento/bootloader do ESP32
                self.serial_conn = serial.Serial(
                    port=porta,
                    baudrate=BAUD_RATE,
                    timeout=1,
                    write_timeout=1,
                    dsrdtr=False,
                    rtscts=False
                )
                self.serial_conn.dtr = False
                self.serial_conn.rts = False
                time.sleep(1.8)  # Tempo do ESP32 inicializar
                self.conectado = True
                self._log(f"[OK] Conectado com sucesso em {porta}!")
                return True, "Conectado"
            except Exception as e:
                self.conectado = False
                erro_msg = str(e)
                if "PermissionError" in erro_msg or "Access is denied" in erro_msg:
                    msg = f"Porta {porta} ocupada! Feche o Monitor Serial do Arduino."
                else:
                    msg = f"Erro em {porta}: {erro_msg}"
                self._log(f"[ERRO] {msg}")
                return False, msg

    def desconectar(self):
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.close()
            except Exception:
                pass
        self.serial_conn = None
        self.conectado = False

    def _log(self, texto):
        if self.callback_log:
            self.callback_log(texto)

    def enviar_angulo(self, servo, angulo, forcar=False):
        angulo = int(max(0, min(ANGULOS_MAX[servo], angulo)))

        if not forcar and abs(self.ultimos_angulos_enviados[servo] - angulo) < 2:
            return

        self.ultimos_angulos_enviados[servo] = angulo
        comando = f"{servo},{angulo}\n"

        if self.conectado and self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(comando.encode("utf-8"))
                self._log(f"-> Servo {servo}: {angulo}°")
            except Exception as e:
                self._log(f"[FALHA ENVIO] {e}")
                self.conectado = False
        else:
            self._log(f"[SIMULAÇÃO] {servo},{angulo}")

    def atualizar_proporcional(self, servo, flexao_0_a_1):
        alvo = flexao_0_a_1 * ANGULOS_MAX[servo]
        self.angulos_suavizados[servo] = (
            SMOOTH_FACTOR * alvo + (1.0 - SMOOTH_FACTOR) * self.angulos_suavizados[servo]
        )
        self.enviar_angulo(servo, int(self.angulos_suavizados[servo]))


# ==========================================================
# INTERFACE GRÁFICA
# ==========================================================
class AppMaoRobotica:
    def __init__(self, root):
        self.root = root
        self.root.title("Controle da Mão Robótica - ESP32")
        self.root.geometry("1100x700")
        self.root.configure(bg="#1a1a1a")

        self.controlador = ControladorMao(callback_log=self.adicionar_log)

        # Variáveis de Estado
        self.modo_camera = tk.BooleanVar(value=False)  # Inicia em Manual para você testar primeiro!
        self.estado_dedos_manual = {i: tk.BooleanVar(value=False) for i in ANGULOS_MAX}
        self.sliders_manual = {}

        # MediaPipe
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.cap = cv2.VideoCapture(0)

        self._construir_interface()

        # Tenta auto-conectar na porta padrão
        self.root.after(500, self.tentar_conexao_inicial)

        self.rodando = True
        self.root.protocol("WM_DELETE_WINDOW", self.ao_fechar)
        self.atualizar_video()

    def _construir_interface(self):
        container = tk.Frame(self.root, bg="#1a1a1a")
        container.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # ------------------ PAINEL ESQUERDO: VÍDEO + LOG ------------------
        col_esquerda = tk.Frame(container, bg="#1a1a1a")
        col_esquerda.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))

        # Câmera
        self.lbl_video = tk.Label(col_esquerda, bg="#0d0d0d", text="Iniciando câmera...", fg="#666")
        self.lbl_video.pack(fill=tk.BOTH, expand=True)

        # Console de Logs (mostra os comandos sendo enviados)
        frame_log = tk.LabelFrame(col_esquerda, text=" Monitor Serial / Log ", font=("Consolas", 9),
                                  fg="#888", bg="#141414", padx=6, pady=4)
        frame_log.pack(fill=tk.X, pady=(8, 0))

        self.txt_log = tk.Text(frame_log, height=4, bg="#0d0d0d", fg="#4af626",
                               font=("Consolas", 9), relief=tk.FLAT)
        self.txt_log.pack(fill=tk.X)

        # ------------------ PAINEL DIREITO: CONTROLES ------------------
        col_direita = tk.Frame(container, bg="#242424", width=360)
        col_direita.pack(side=tk.RIGHT, fill=tk.Y)

        # 1. Conexão Serial
        frame_serial = tk.LabelFrame(col_direita, text=" Conexão ESP32 ", font=("Segoe UI", 9, "bold"),
                                     fg="#61afef", bg="#242424", padx=8, pady=8)
        frame_serial.pack(fill=tk.X, padx=12, pady=(10, 6))

        linha_porta = tk.Frame(frame_serial, bg="#242424")
        linha_porta.pack(fill=tk.X, pady=2)

        tk.Label(linha_porta, text="Porta:", fg="#fff", bg="#242424").pack(side=tk.LEFT)
        self.combo_portas = ttk.Combobox(linha_porta, width=9, state="readonly")
        self.combo_portas.pack(side=tk.LEFT, padx=6)
        self.atualizar_lista_portas()

        self.btn_conectar = tk.Button(linha_porta, text="Conectar", bg="#61afef", fg="#000",
                                      font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                                      command=self.conectar_porta)
        self.btn_conectar.pack(side=tk.LEFT, padx=2)

        btn_atualizar = tk.Button(linha_porta, text="🔄", bg="#3a3a3a", fg="#fff",
                                  relief=tk.FLAT, command=self.atualizar_lista_portas)
        btn_atualizar.pack(side=tk.LEFT, padx=2)

        # Badge de Status (Verde ou Vermelho)
        self.lbl_status_conexao = tk.Label(
            frame_serial, text="🔴 DESCONECTADO", font=("Segoe UI", 9, "bold"),
            fg="#ff5555", bg="#242424"
        )
        self.lbl_status_conexao.pack(anchor=tk.W, pady=(4, 0))

        # 2. Modo de Operação
        frame_modo = tk.LabelFrame(col_direita, text=" Modo ", font=("Segoe UI", 9, "bold"),
                                   fg="#e5c07b", bg="#242424", padx=10, pady=6)
        frame_modo.pack(fill=tk.X, padx=12, pady=6)

        rb_man = tk.Radiobutton(
            frame_modo, text="🎛️ Manual (Interfaçe interativa)",
            variable=self.modo_camera, value=False,
            font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#242424",
            selectcolor="#333", activebackground="#242424",
            command=self.alternar_modo
        )
        rb_man.pack(anchor=tk.W, pady=2)

        rb_cam = tk.Radiobutton(
            frame_modo, text="📹 Câmera (Proporcional Suave)",
            variable=self.modo_camera, value=True,
            font=("Segoe UI", 10), fg="#ffffff", bg="#242424",
            selectcolor="#333", activebackground="#242424",
            command=self.alternar_modo
        )
        rb_cam.pack(anchor=tk.W, pady=2)

        # 3. Ações Rápidas
        self.frame_rapido = tk.Frame(col_direita, bg="#242424")
        self.frame_rapido.pack(fill=tk.X, padx=12, pady=4)

        self.btn_todos_abrir = tk.Button(
            self.frame_rapido, text="✋ Abrir Todos (0°)", bg="#388e3c", fg="white",
            font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
            command=lambda: self.definir_todos(False)
        )
        self.btn_todos_abrir.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))

        self.btn_todos_fechar = tk.Button(
            self.frame_rapido, text="✊ Fechar Todos", bg="#d32f2f", fg="white",
            font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
            command=lambda: self.definir_todos(True)
        )
        self.btn_todos_fechar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(3, 0))

        # 4. Dedos Individuais
        self.frame_dedos = tk.LabelFrame(col_direita, text=" Controle Individual ",
                                         font=("Segoe UI", 9, "bold"), fg="#98c379",
                                         bg="#242424", padx=8, pady=6)
        self.frame_dedos.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        dedos_info = [
            (1, "Polegar"),
            (2, "Indicador"),
            (4, "Médio"),
            (3, "Anelar"),
            (5, "Mínimo")
        ]

        self.botoes_toggle = {}

        for servo_id, nome in dedos_info:
            linha = tk.Frame(self.frame_dedos, bg="#242424")
            linha.pack(fill=tk.X, pady=3)

            lbl = tk.Label(linha, text=nome, width=8, anchor="w",
                           font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#242424")
            lbl.pack(side=tk.LEFT)

            btn = tk.Button(
                linha, text="Aberto", width=7, bg="#333", fg="#4caf50",
                font=("Segoe UI", 8, "bold"), relief=tk.FLAT,
                command=lambda s=servo_id: self.toggle_dedo_manual(s)
            )
            btn.pack(side=tk.LEFT, padx=4)
            self.botoes_toggle[servo_id] = btn

            slider = tk.Scale(
                linha, from_=0, to=ANGULOS_MAX[servo_id], orient=tk.HORIZONTAL,
                bg="#242424", fg="#aaa", highlightthickness=0,
                troughcolor="#161616", activebackground="#61afef",
                command=lambda val, s=servo_id: self.ao_mover_slider(s, val)
            )
            slider.pack(side=tk.RIGHT, fill=tk.X, expand=True)
            self.sliders_manual[servo_id] = slider

        self.alternar_modo()

    # ================= GERENCIAMENTO DE CONEXÃO =================
    def atualizar_lista_portas(self):
        portas = [p.device for p in serial.tools.list_ports.comports()]
        self.combo_portas["values"] = portas
        if portas:
            if "COM3" in portas:
                self.combo_portas.set("COM3")
            else:
                self.combo_portas.set(portas[0])
        else:
            self.combo_portas.set("")

    def tentar_conexao_inicial(self):
        porta = self.combo_portas.get()
        if porta:
            self.conectar_porta()

    def conectar_porta(self):
        porta = self.combo_portas.get()
        if not porta:
            messagebox.showwarning("Aviso", "Nenhuma porta serial detectada!")
            return

        ok, msg = self.controlador.conectar(porta)
        if ok:
            self.lbl_status_conexao.config(text=f"🟢 CONECTADO ({porta})", fg="#4caf50")
            self.btn_conectar.config(text="Reconectar")
        else:
            self.lbl_status_conexao.config(text=f"🔴 ERRO: {msg}", fg="#ff5555")

    def adicionar_log(self, texto):
        if not hasattr(self, 'txt_log'):
            return
        self.txt_log.insert(tk.END, texto + "\n")
        self.txt_log.see(tk.END)
        # Limita o tamanho do log
        linhas = int(self.txt_log.index('end-1c').split('.')[0])
        if linhas > 40:
            self.txt_log.delete("1.0", "15.0")

    # ================= MODO MANUAL =================
    def alternar_modo(self):
        ativo_manual = not self.modo_camera.get()
        estado = tk.NORMAL if ativo_manual else tk.DISABLED

        self.btn_todos_abrir.config(state=estado)
        self.btn_todos_fechar.config(state=estado)

        for s in ANGULOS_MAX:
            self.botoes_toggle[s].config(state=estado)
            self.sliders_manual[s].config(state=estado)

    def toggle_dedo_manual(self, servo):
        if self.modo_camera.get():
            return
        novo_estado = not self.estado_dedos_manual[servo].get()
        self.estado_dedos_manual[servo].set(novo_estado)
        self._aplicar_estado_manual(servo, novo_estado)

    def definir_todos(self, fechado):
        if self.modo_camera.get():
            return
        for s in ANGULOS_MAX:
            self.estado_dedos_manual[s].set(fechado)
            self._aplicar_estado_manual(s, fechado)

    def _aplicar_estado_manual(self, servo, fechado):
        btn = self.botoes_toggle[servo]
        slider = self.sliders_manual[servo]

        if fechado:
            btn.config(text="Fechado", fg="#f44336")
            slider.set(ANGULOS_MAX[servo])
            self.controlador.enviar_angulo(servo, ANGULOS_MAX[servo], forcar=True)
        else:
            btn.config(text="Aberto", fg="#4caf50")
            slider.set(ANGULO_ABERTO)
            self.controlador.enviar_angulo(servo, ANGULO_ABERTO, forcar=True)

    def ao_mover_slider(self, servo, valor):
        if self.modo_camera.get():
            return
        angulo = int(valor)
        self.controlador.enviar_angulo(servo, angulo)

        if angulo > ANGULOS_MAX[servo] / 2:
            self.botoes_toggle[servo].config(text="Fechado", fg="#f44336")
            self.estado_dedos_manual[servo].set(True)
        else:
            self.botoes_toggle[servo].config(text="Aberto", fg="#4caf50")
            self.estado_dedos_manual[servo].set(False)

    # ================= MODO CÂMERA =================
    def atualizar_video(self):
        if not self.rodando:
            return

        ok, frame = self.cap.read()
        if ok:
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resultado = self.hands.process(rgb)

            if resultado.multi_hand_landmarks and self.modo_camera.get():
                landmarks = resultado.multi_hand_landmarks[0]
                self.mp_draw.draw_landmarks(frame, landmarks, self.mp_hands.HAND_CONNECTIONS)

                pts = [(int(p.x * w), int(p.y * h)) for p in landmarks.landmark]

                # Distância base da palma para normalização
                ref_palma = math.hypot(pts[9][0] - pts[0][0], pts[9][1] - pts[0][1])
                if ref_palma < 1:
                    ref_palma = 1

                # 1. Polegar
                dist_pol = math.hypot(pts[4][0] - pts[17][0], pts[4][1] - pts[17][1])
                flex_pol = 1.0 - max(0.0, min(1.0, ((dist_pol / ref_palma) - 0.55) / (1.20 - 0.55)))

                # 2. Indicador
                dist_ind = math.hypot(pts[8][0] - pts[0][0], pts[8][1] - pts[0][1])
                flex_ind = 1.0 - max(0.0, min(1.0, ((dist_ind / ref_palma) - 0.90) / (1.90 - 0.90)))

                # 4. Médio
                dist_med = math.hypot(pts[12][0] - pts[0][0], pts[12][1] - pts[0][1])
                flex_med = 1.0 - max(0.0, min(1.0, ((dist_med / ref_palma) - 0.90) / (2.00 - 0.90)))

                # 3. Anelar
                dist_ane = math.hypot(pts[16][0] - pts[0][0], pts[16][1] - pts[0][1])
                flex_ane = 1.0 - max(0.0, min(1.0, ((dist_ane / ref_palma) - 0.85) / (1.85 - 0.85)))

                # 5. Mínimo
                dist_min = math.hypot(pts[20][0] - pts[0][0], pts[20][1] - pts[0][1])
                flex_min = 1.0 - max(0.0, min(1.0, ((dist_min / ref_palma) - 0.75) / (1.65 - 0.75)))

                self.controlador.atualizar_proporcional(1, flex_pol)
                self.controlador.atualizar_proporcional(2, flex_ind)
                self.controlador.atualizar_proporcional(4, flex_med)
                self.controlador.atualizar_proporcional(3, flex_ane)
                self.controlador.atualizar_proporcional(5, flex_min)

                cv2.putText(frame, "MODO: CAMERA (PROPORCIONAL)", (15, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            elif not self.modo_camera.get():
                cv2.putText(frame, "MODO: MANUAL (GUI)", (15, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb).resize((560, 420), Image.Resampling.LANCZOS)
            img_tk = ImageTk.PhotoImage(image=img_pil)

            self.lbl_video.img_tk = img_tk
            self.lbl_video.configure(image=img_tk)

        self.root.after(30, self.atualizar_video)

    def ao_fechar(self):
        self.rodando = False
        self.hands.close()
        self.cap.release()
        self.controlador.desconectar()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AppMaoRobotica(root)
    root.mainloop()
