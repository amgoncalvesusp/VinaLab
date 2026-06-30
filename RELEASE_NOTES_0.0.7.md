# VinaLab v0.0.7

## Correção de bugs

### Conversão de receptor para PDBQT (corrigido)
- A preparação de receptor com o Meeko (`mk_prepare_receptor`) falhava em
  praticamente qualquer estrutura cristalográfica real porque o arquivo continha
  resíduos com **localização alternativa (altloc)** — o Meeko abortava com
  "Creation of data structure for receptor failed". A conversão agora usa
  `--default_altloc` (além de `--allow_bad_res`), preparando o receptor
  corretamente. Validado no executável empacotado (ex.: 6LJ1 → PDBQT válido).
- Corrigido um falso "sucesso" quando já existia um `.pdbqt` antigo na saída: a
  conversão agora apaga a saída antes e só reporta sucesso se o arquivo for
  realmente gerado; em caso de falha, a mensagem traz o erro real do Meeko.

### GNINA empacotado em todas as builds
- O GNINA deixava de ser incluído no release porque o empacotamento dependia de
  o `gnina.exe` iniciar na máquina de build do CI (que não tem GPU/driver). Agora
  o GNINA é sempre empacotado quando presente no repositório; a disponibilidade
  real é decidida no PC do usuário em tempo de execução.

## Observações
- As funções de pontuação por machine learning (RTMScore, DeltaVinaXGB) dependem
  de bibliotecas pesadas (torch/dgl, >1 GB) que não cabem no executável e
  permanecem como recurso opcional separado.
