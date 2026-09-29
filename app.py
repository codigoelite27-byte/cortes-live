import streamlit as st
import tempfile
import os
import subprocess
import whisper
import html

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
    max_value=300,
    value=60,
    step=15
)

modelo = st.selectbox(
    "Qualidade da legenda",
    ["tiny", "base"]
)

if video:

    if st.button("✂️ Gerar cortes com legenda"):

        with tempfile.TemporaryDirectory() as pasta:

            entrada = os.path.join(pasta, "video.mp4")

            with open(entrada, "wb") as f:
                f.write(video.read())

            st.info("1/4 — Gerando os cortes...")

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i", entrada,
                    "-c", "copy",
                    "-map", "0",
                    "-f", "segment",
                    "-segment_time", str(duracao),
                    "-reset_timestamps", "1",
                    os.path.join(pasta, "corte_%03d.mp4")
                ],
                check=True
            )

            arquivos = sorted(
                os.path.join(pasta, x)
                for x in os.listdir(pasta)
                if x.startswith("corte_") and x.endswith(".mp4")
            )

            if not arquivos:
                st.error("Não foi possível gerar os cortes.")
                st.stop()

            st.info("2/4 — Carregando modelo de legenda...")

            model = whisper.load_model(modelo)

            videos_finais = []
            legendas = []

            st.info("3/4 — Transcrevendo os cortes...")

            for i, arquivo in enumerate(arquivos):

                resultado = model.transcribe(
                    arquivo,
                    language="pt",
                    fp16=False
                )

                # -----------------------------
                # CRIA O SRT
                # -----------------------------

                srt = os.path.splitext(arquivo)[0] + ".srt"

                def tempo(segundos):
                    horas = int(segundos // 3600)
                    minutos = int((segundos % 3600) // 60)
                    segundos_int = int(segundos % 60)
                    milissegundos = int(
                        (segundos - int(segundos)) * 1000
                    )

                    return (
                        f"{horas:02d}:"
                        f"{minutos:02d}:"
                        f"{segundos_int:02d},"
                        f"{milissegundos:03d}"
                    )

                with open(srt, "w", encoding="utf-8") as f:

                    for n, segmento in enumerate(
                        resultado["segments"], 1
                    ):

                        inicio = segmento["start"]
                        fim = segmento["end"]
                        texto = segmento["text"].strip()

                        f.write(f"{n}\n")
                        f.write(
                            f"{tempo(inicio)} --> "
                            f"{tempo(fim)}\n"
                        )
                        f.write(f"{texto}\n\n")

                legendas.append(srt)

                st.write(
                    f"Transcrição: {i + 1}/{len(arquivos)}"
                )

                # -----------------------------
                # CRIA ASS PARA LEGENDA ESTILIZADA
                # -----------------------------

                ass = os.path.splitext(arquivo)[0] + ".ass"

                with open(ass, "w", encoding="utf-8") as f:

                    f.write(
                        "[Script Info]\n"
                        "ScriptType: v4.00+\n"
                        "PlayResX: 1080\n"
                        "PlayResY: 1920\n\n"
                    )

                    f.write(
                        "[V4+ Styles]\n"
                        "Format: Name, Fontname, Fontsize, "
                        "PrimaryColour, SecondaryColour, "
                        "OutlineColour, BackColour, Bold, "
                        "Italic, Underline, StrikeOut, "
                        "ScaleX, ScaleY, Spacing, Angle, "
                        "BorderStyle, Outline, Shadow, "
                        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
                    )

                    # Legenda grande, branca, com contorno preto
                    f.write(
                        "Style: Default,Arial,64,"
                        "&H00FFFFFF,"
                        "&H0000FFFF,"
                        "&H00000000,"
                        "&H80000000,"
                        "1,0,0,0,"
                        "100,100,2,0,"
                        "1,5,2,"
                        "2,70,70,430,1\n\n"
                    )

                    f.write("[Events]\n")
                    f.write(
                        "Format: Layer, Start, End, Style, "
                        "Name, MarginL, MarginR, MarginV, "
                        "Effect, Text\n"
                    )

                    for segmento in resultado["segments"]:

                        inicio = segmento["start"]
                        fim = segmento["end"]
                        texto = segmento["text"].strip()

                        if not texto:
                            continue

                        def ass_tempo(segundos):
                            horas = int(segundos // 3600)
                            minutos = int((segundos % 3600) // 60)
                            segundos_int = int(segundos % 60)
                            centesimos = int(
                                (segundos - int(segundos)) * 100
                            )

                            return (
                                f"{horas}:"
                                f"{minutos:02d}:"
                                f"{segundos_int:02d}."
                                f"{centesimos:02d}"
                            )

                        # Quebra textos muito longos em duas linhas
                        palavras = texto.split()

                        linhas = []
                        linha = ""

                        for palavra in palavras:

                            teste = (
                                linha + " " + palavra
                            ).strip()

                            if len(teste) > 28:
                                if linha:
                                    linhas.append(linha)
                                linha = palavra
                            else:
                                linha = teste

                        if linha:
                            linhas.append(linha)

                        texto_final = "\\N".join(linhas)

                        texto_final = (
                            texto_final
                            .replace("{", "")
                            .replace("}", "")
                        )

                        f.write(
                            f"Dialogue: 0,"
                            f"{ass_tempo(inicio)},"
                            f"{ass_tempo(fim)},"
                            f"Default,,0,0,0,,"
                            f"{texto_final}\n"
                        )

                # -----------------------------
                # GERA VÍDEO VERTICAL 9:16
                # COM FUNDO DESFOCADO
                # -----------------------------

                saida = os.path.join(
                    pasta,
                    f"reels_{i + 1:03d}.mp4"
                )

                filtro = (
                    "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
                    "crop=1080:1920,"
                    "boxblur=30:10,"
                    "setsar=1,"
                    "eq=brightness=-0.10[bg];"

                    "[0:v]scale=1080:608:force_original_aspect_ratio=decrease,"
                    "setsar=1[fg];"

                    "[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                    f"subtitles='{ass}'"
                )

                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i", arquivo,
                        "-filter_complex", filtro,
                        "-map", "0:v:0",
                        "-map", "0:a?",
                        "-c:v", "libx264",
                        "-preset", "veryfast",
                        "-crf", "23",
                        "-c:a", "aac",
                        "-b:a", "128k",
                        "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart",
                        saida
                    ],
                    check=True
                )

                videos_finais.append(saida)

            st.info("4/4 — Finalizando os vídeos...")

            st.success(
                f"✅ {len(videos_finais)} cortes prontos para Reels/TikTok!"
            )

            # -----------------------------
            # MOSTRA O PRIMEIRO CORTE
            # -----------------------------

            st.subheader("🎬 Primeiro corte pronto")

            st.video(videos_finais[0])

            with open(videos_finais[0], "rb") as f:
                video_bytes = f.read()

            st.download_button(
                "⬇️ Baixar primeiro corte — 9:16 + legenda",
                data=video_bytes,
                file_name="corte_reels_001.mp4",
                mime="video/mp4"
            )

            # -----------------------------
            # LEGENDA SRT
            # -----------------------------

            with open(legendas[0], "rb") as f:
                srt_bytes = f.read()

            st.download_button(
                "📝 Baixar legenda (.srt)",
                data=srt_bytes,
                file_name="corte_001.srt",
                mime="text/plain"
            )
