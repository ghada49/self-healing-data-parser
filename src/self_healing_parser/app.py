import gradio as gr
from self_healing_parser.agent.agent import process_data


with gr.Blocks(theme=gr.themes.Monochrome()) as app:
    gr.Markdown("# Self-Healing Data Parser")
    gr.Markdown("Agent writes code, tests it, fixes it, and returns clean JSON.")

    with gr.Row():
        with gr.Column():
            raw_text = gr.Textbox(lines=12, label="Messy Raw Text")
            requirements = gr.Textbox(lines=3, label="Extraction Requirements")
            provider = gr.Radio(["openai", "ollama"], value="openai", label="Provider")
            model_openai = gr.Textbox(value="gpt-4o-mini", label="OpenAI model")
            model_ollama = gr.Textbox(value="gpt-oss:20b", label="Ollama model")
            btn = gr.Button("Extract")

        with gr.Column():
            status = gr.Markdown()
            extracted = gr.Code(language="json")
            code = gr.Code(language="python")

    def route(raw_text, reqs, provider, m_openai, m_ollama):
        model = m_openai if provider == "openai" else m_ollama
        yield from process_data(raw_text, reqs, provider, model)

    btn.click(
        route,
        inputs=[raw_text, requirements, provider, model_openai, model_ollama],
        outputs=[status, extracted, code],
    )

if __name__ == "__main__":
    app.launch()
