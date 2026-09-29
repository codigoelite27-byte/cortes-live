import streamlit as st
import tempfile
import os
import subprocess
import whisper

st.set_page_config(
    page_title="Cortes de Lives",
    page_icon="✂️"
)

st.title("✂️ Cortes de Lives")
st.write("Gere cortes com legenda automática.")

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

            st.info("1/3 — Gerando os cortes...")

            subprocess.run(
                [
                    "ffmpeg",
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

            st.info("2/3 — Carregando modelo de legenda...")

            model = whisper.load_model(modelo)

            st.info("3/3 — Gerando legendas...")

            for i, arquivo in enumerate(arquivos):

                resultado = model.transcribe(
                    arquivo,
                    language="pt",
                    fp16=False
                )

                srt = os.path.splitext(arquivo)[0] + ".srt"

                with open(srt, "w", encoding="utf-8") as f:

                    for n, segmento in enumerate(
                        resultado["segments"], 1
                    ):

                        inicio = segmento["start"]
                        fim = segmento["end"]
                        texto = segmento["text"].strip()

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

                        f.write(f"{n}\n")
                        f.write(
                            f"{tempo(inicio)} --> "
                            f"{tempo(fim)}\n"
                        )
                        f.write(f"{texto}\n\n")

                st.write(
                    f"Legenda gerada: "
                    f"{i + 1}/{len(arquivos)}"
                )

            st.success(
                f"✅ {len(arquivos)} cortes gerados!"
            )

            st.download_button(
                "⬇️ Baixar primeiro corte",
                data=open(arquivos[0], "rb").read(),
                file_name=os.path.basename(arquivos[0]),
                mime="video/mp4"
            )

            primeiro_srt = os.path.splitext(
                arquivos[0]
            )[0] + ".srt"

            st.download_button(
                "📝 Baixar legenda do primeiro corte",
                data=open(
                    primeiro_srt,
                    "rb"
                ).read(),
                file_name=os.path.basename(primeiro_srt),
                mime="text/plain"
            )
