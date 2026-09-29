import streamlit as st
import tempfile
import os
import subprocess
import whisper
import gc

st.set_page_config(
    page_title="Cortes de Lives",
    page_icon="✂️"
)

st.title("✂️ Cortes de Lives")
st.write("Gere cortes verticais com legenda automática para TikTok, Reels e Shorts.")

video = st.file_uploader(
    "Envie sua live ou vídeo",
    type=["mp4", "mov", "mkv", "avi", "webm"]
)

duracao = st.number_input(
    "Duração de cada corte (segundos)",
    min_value=15,
    max_value=120,
    value=60,
    step=15
)

modelo = st.selectbox(
    "Qualidade da legenda",
    ["tiny", "base"],
    index=0
)

quantidade = st.number_input(
    "Quantidade de cortes para gerar",
    min_value=1,
    max_value=10,
    value=1,
    step=1
)


if video:

    if st.button("✂️ Gerar cortes com legenda"):

        with tempfile.TemporaryDirectory() as pasta:

            # =====================================================
            # 1 — SALVA O VÍDEO
            # =====================================================

            st.info("1/4 — Preparando o vídeo...")

            entrada = os.path.join(pasta, "video.mp4")

            with open(entrada, "wb") as f:
                f.write(video.getbuffer())

            del video
            gc.collect()

            # =====================================================
            # 2 — GERA OS CORTES
            # =====================================================

            st.info("2/4 — Gerando os cortes...")

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i", entrada,
                    "-c", "copy",
                    "-map", "0:v:0",
                    "-map", "0:a?",
                    "-f", "segment",
                    "-segment_time", str(duracao),
                    "-reset_timestamps", "1",
                    os.path.join(
                        pasta,
                        "corte_%03d.mp4"
                    )
                ],
                check=True
            )

            arquivos = sorted(
                os.path.join(pasta, x)
                for x in os.listdir(pasta)
                if x.startswith("corte_")
                and x.endswith(".mp4")
            )

            if not arquivos:
                st.error(
                    "Não foi possível gerar os cortes."
                )
                st.stop()

            arquivos = arquivos[:quantidade]

            st.write(
                f"Serão processados {len(arquivos)} cortes."
            )

            # =====================================================
            # 3 — WHISPER
            # =====================================================

            st.info(
                "3/4 — Carregando modelo de legenda..."
            )

            model = whisper.load_model(modelo)

            videos_finais = []
            legendas = []

            for i, arquivo in enumerate(arquivos):

                st.write(
                    f"🎙️ Transcrevendo corte "
                    f"{i + 1}/{len(arquivos)}..."
                )

                # -------------------------------------------------
                # TRANSCRIÇÃO
                # -------------------------------------------------

                resultado = model.transcribe(
                    arquivo,
                    language="pt",
                    fp16=False,
                    temperature=0
                )

                # =================================================
                # SRT
                # =================================================

                srt = os.path.splitext(
                    arquivo
                )[0] + ".srt"

                def tempo(segundos):

                    horas = int(
                        segundos // 3600
                    )

                    minutos = int(
                        (segundos % 3600) // 60
                    )

                    segundos_int = int(
                        segundos % 60
                    )

                    milissegundos = int(
                        (segundos - int(segundos)) * 1000
                    )

                    return (
                        f"{horas:02d}:"
                        f"{minutos:02d}:"
                        f"{segundos_int:02d},"
                        f"{milissegundos:03d}"
                    )

                with open(
                    srt,
                    "w",
                    encoding="utf-8"
                ) as f:

                    numero = 1

                    for segmento in resultado["segments"]:

                        inicio = segmento["start"]
                        fim = segmento["end"]

                        texto = (
                            segmento["text"]
                            .strip()
                        )

                        if not texto:
                            continue

                        f.write(
                            f"{numero}\n"
                        )

                        f.write(
                            f"{tempo(inicio)} --> "
                            f"{tempo(fim)}\n"
                        )

                        f.write(
                            f"{texto}\n\n"
                        )

                        numero += 1

                legendas.append(srt)

                # =================================================
                # VÍDEO VERTICAL
                # =================================================

                st.write(
                    f"🎬 Renderizando corte "
                    f"{i + 1}/{len(arquivos)}..."
                )

                saida = os.path.join(
                    pasta,
                    f"reels_{i + 1:03d}.mp4"
                )

                # -------------------------------------------------
                # FUNDO + VÍDEO
                # -------------------------------------------------

                filtro_video = (
                    "[0:v]"
                    "scale=1080:1920:"
                    "force_original_aspect_ratio=increase,"
                    "crop=1080:1920,"
                    "boxblur=30:10,"
                    "setsar=1,"
                    "eq=brightness=-0.10"
                    "[bg];"

                    "[0:v]"
                    "scale=1080:608:"
                    "force_original_aspect_ratio=decrease,"
                    "setsar=1"
                    "[fg];"

                    "[bg][fg]"
                    "overlay=(W-w)/2:(H-h)/2"
                    "[v]"
                )

                # -------------------------------------------------
                # LEGENDA DIRETO DO SRT
                # -------------------------------------------------

                # Caminho absoluto escapado para FFmpeg
                srt_ffmpeg = srt.replace(
                    "\\",
                    "/"
                ).replace(
                    ":",
                    "\\:"
                )

                filtro = (
                    filtro_video
                    + ";[v]"
                    + f"subtitles='{srt_ffmpeg}'"
                    + ":force_style='"
                    "FontName=DejaVu Sans,"
                    "FontSize=64,"
                    "PrimaryColour=&H00FFFFFF,"
                    "OutlineColour=&H00000000,"
                    "BorderStyle=1,"
                    "Outline=5,"
                    "Shadow=2,"
                    "Bold=1,"
                    "Alignment=2,"
                    "MarginV=430"
                    "'"
                )

                # -------------------------------------------------
                # FFMPEG
                # -------------------------------------------------

                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",

                        "-i",
                        arquivo,

                        "-filter_complex",
                        filtro,

                        "-map",
                        "0:v:0",

                        "-map",
                        "0:a?",

                        "-c:v",
                        "libx264",

                        "-preset",
                        "ultrafast",

                        "-crf",
                        "27",

                        "-c:a",
                        "aac",

                        "-b:a",
                        "96k",

                        "-pix_fmt",
                        "yuv420p",

                        "-movflags",
                        "+faststart",

                        saida
                    ],
                    check=True
                )

                videos_finais.append(
                    saida
                )

                # Lib
