import streamlit as st
import tempfile
import os
import subprocess

st.set_page_config(page_title="Cortes de Lives", page_icon="✂️")

st.title("✂️ Cortes de Lives")
st.write("Gere vários trechos de um vídeo automaticamente.")

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

if video:
    if st.button("✂️ Gerar cortes"):
        with tempfile.TemporaryDirectory() as pasta:

            entrada = os.path.join(pasta, "video.mp4")

            with open(entrada, "wb") as f:
                f.write(video.read())

            st.info("Gerando os cortes...")

            resultado = subprocess.run(
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
                capture_output=True,
                text=True
            )

            arquivos = sorted(
                os.path.join(pasta, x)
                for x in os.listdir(pasta)
                if x.startswith("corte_") and x.endswith(".mp4")
            )

            if not arquivos:
                st.error("Não foi possível gerar os cortes.")
            else:
                st.success(f"{len(arquivos)} cortes gerados!")

                for arquivo in arquivos:
                    with open(arquivo, "rb") as f:
                        st.download_button(
                            f"⬇️ Baixar {os.path.basename(arquivo)}",
                            f,
                            file_name=os.path.basename(arquivo),
                            mime="video/mp4"
                        )
