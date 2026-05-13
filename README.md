# Cards Litoral — COGERH / GRLITORAL

Gerador local de cards de monitoramento de reservatórios da **Bacia do Litoral**.
Não depende de Railway, Heroku ou qualquer servidor externo.

## Estrutura necessária

```
pasta/
├── app.py
├── engine.py
├── base_card.png
├── cav.csv
├── requirements.txt
└── fonts/
    ├── DejaVuSans.ttf
    └── DejaVuSans-Bold.ttf
```

## Instalação (primeira vez)

```bash
pip install -r requirements.txt
```

## Execução

```bash
streamlit run app.py
```

O navegador abrirá automaticamente em `http://localhost:8501`.

## Uso

1. Cole o link da planilha Google Sheets na sidebar (ou mantenha o padrão).
2. Informe o GID da aba (0 = primeira aba).
3. Escolha modo, formato e ordenação.
4. Clique em **"Carregar planilha e gerar cards"**.
5. Visualize o preview e clique em **Baixar** para salvar o arquivo.

## Filtro de bacia

O app filtra automaticamente os registros com `BACIA = Litoral` e `GERÊNCIA = GRLITORAL`.
Nenhuma outra bacia é processada ou exibida.

## Lookup CAV

Ative "Abrir consulta CAV" na sidebar para consultar cota/área/volume
a partir de barrote + leitura de régua, limitado aos reservatórios da bacia Litoral.
