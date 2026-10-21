<div align="center">

# 🤖 Mão Robótica Controlada por Visão Computacional
### *Real-Time Hand Tracking & Bio-Inspired Robotic Teleoperation*

<!-- Badges de Tecnologias e Hardware -->
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0097A7?style=for-the-badge&logo=google&logoColor=white)](https://mediapipe.dev)
[![ESP32-C3](https://img.shields.io/badge/ESP32--C3_Super_Mini-E7352C?style=for-the-badge&logo=espressif&logoColor=white)](https://espressif.com)
[![C++](https://img.shields.io/badge/C++-00599C?style=for-the-badge&logo=cplusplus&logoColor=white)](https://isocpp.org)
[![3D Printing](https://img.shields.io/badge/3D_Printing-FDM-FF6F00?style=for-the-badge&logo=makerbot&logoColor=white)](https://en.wikipedia.org/wiki/3D_printing)

<br/>

<!-- Typing SVG dinâmico -->
<a href="https://github.com/DenverCoder1/readme-typing-svg">
  <img src="https://readme-typing-svg.demolab.com/?lines=Vis%C3%A3o+Computacional+%26+Deep+Learning+(MediaPipe);Rastreamento+Articular+em+Tempo+Real;Controle+Cinem%C3%A1tico+Proporcional+com+ESP32-C3;Automa%C3%A7%C3%A3o%2C+IoT+%26+Intera%C3%A7%C3%A3o+Homem-M%C3%A1quina&font=Fira%20Code&center=true&width=650&height=35&color=88e788&vCenter=true&pause=800&size=16" alt="Typing SVG" />
</a>

<p align="center">
  Sistema biomimético teleoperado capaz de espelhar o movimento individual e proporcional dos dedos humanos em tempo real via câmera.
</p>

</div>

---

<!-- ==================== DEMONSTRAÇÃO DO PROJETO ==================== -->

<p align="center">
  <img src="https://github.com/DiegoTarcisio/Mao-robotica-visao-computacional/raw/main/assets/mao.gif" alt="Demonstração da Mão Robótica" width="300" />
</p>





---

<!-- ==================== SOBRE O PROJETO ==================== -->
<details open>
  <summary><b>📌 Sobre o Projeto</b></summary><br/>

  <p align="justify">
    Este projeto consiste no desenvolvimento de uma <b>prótese robótica antropomórfica impressa em 3D</b> acionada por cabos de tração (tendões sintéticos) e teleoperada em tempo real por <b>visão computacional</b>. 
  </p>
  <p align="justify">
    Uma câmera comum captura os gestos da mão humana, enquanto algoritmos em <b>Python</b> processam a imagem utilizando <b>MediaPipe Hands</b> e <b>OpenCV</b> para extrair as coordenadas espaciais das 21 articulações anatômicas. O grau de flexão de cada dedo é calculado matematicamente e transmitido ao microcontrolador <b>ESP32-C3 Super Mini</b>, que atua em cinco servomotores <b>SG90</b> de forma suave e proporcional, garantindo uma resposta natural e baixa latência.
  </p>

  <b>Principais Destaques:</b>
  <ul>
    <li><b>Controle Proporcional Dedicado:</b> Movimentação independente de cada dedo (Polegar, Indicador, Médio, Anelar e Mínimo).</li>
    <li><b>Sem Sensores Wearables:</b> Dispensa o uso de luvas ou sensores acoplados ao usuário.</li>
    <li><b>Arquitetura Biomimética:</b> Estrutura anatômica com tendões flexíveis e recuo assistido.</li>
    <li><b>Acessibilidade e Baixo Custo:</b> Fabricação por manufatura aditiva (FDM) e eletrônica de fácil aquisição.</li>
  </ul>
</details>

<br/>

<!-- ==================== ARQUITETURA E FLUXO ==================== -->
<details open>
  <summary><b>🧠 Arquitetura do Sistema & Pipeline</b></summary><br/>

  ```mermaid
  graph LR
    A[📹 Câmera / Webcam] --> B[🐍 Python / OpenCV]
    B --> C[🖐️ MediaPipe Hands 21 Landmarks]
    C --> D[📐 Cálculo de Abertura & Normalização 0°-180°]
    D --> E[📡 Comunicação Serial / UART]
    E --> F[⚡ ESP32-C3 Super Mini]
    F --> G[⚙️ 5x Servos SG90 PWM]
    G --> H[🦾 Mão Robótica Impressa em 3D]
