# VinaLab 1.0.1

## English

### Windows packaging

- GNINA is not included in Windows builds anymore.
- The Windows scoring selector hides GNINA instead of showing it disabled.
- Windows builds no longer collect `c10.dll`, `torch_cpu.dll`, or `torch_cuda.dll`.
- GNINA remains a Linux/WSL path until a complete native Windows bundle is validated.
- SMINA is available as an optional backend when `smina`/`smina.exe` is found in `tools/smina`, PATH, or Conda. It is not required by the installer.

### Docking and conversion

- Vina and Vinardo remain the primary native scoring functions on Windows.
- The bundled AutoDock Vina CLI fallback now runs with `native_tool_env`.
- Runtime checks now require RDKit, Meeko, `meeko.cli.mk_prepare_receptor`, Open Babel, `obabel`, Open Babel `.obf` plugins, `openbabel_wheel.libs`, and the Vina CLI.
- Added regression and optional smoke tests for conversion, Vina CLI docking, and Windows release contents.

## Portugues

### Empacotamento Windows

- GNINA nao e mais incluido nos builds Windows.
- O seletor de pontuacao no Windows oculta GNINA em vez de exibir a opcao desabilitada.
- Builds Windows nao coletam mais `c10.dll`, `torch_cpu.dll` ou `torch_cuda.dll`.
- GNINA fica reservado para Linux/WSL ate existir um bundle Windows nativo completo e validado.
- SMINA fica disponivel como backend opcional quando `smina`/`smina.exe` for encontrado em `tools/smina`, PATH ou Conda. Ele nao e requisito do instalador.

### Docking e conversao

- Vina e Vinardo continuam como funcoes nativas principais no Windows.
- O fallback AutoDock Vina CLI incluido agora roda com `native_tool_env`.
- A checagem de runtime agora exige RDKit, Meeko, `meeko.cli.mk_prepare_receptor`, Open Babel, `obabel`, plugins `.obf`, `openbabel_wheel.libs` e Vina CLI.
- Foram adicionados testes de regressao e smoke tests opcionais para conversao, docking pelo Vina CLI e conteudo do release Windows.
