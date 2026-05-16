# Changelog

## 0.0.2 - 2026-05-16

- Adiciona GitHub Actions para gerar builds nativos de Windows, macOS e Linux a partir de tags `v*`.
- Adiciona empacotamento automatizado dos artefatos e criação de GitHub Release.
- Atualiza README bilíngue com inglês primeiro e português em seguida.
- Mantém dependências opcionais de pontuação fora do bootstrap automático.

## 0.0.1 - 2026-05-16

- Primeira versão pública como VinaLab.
- Corrige o pacote Windows para abrir o aplicativo compilado diretamente, sem bootstrap de `.venv` no primeiro uso.
- O instalador Windows agora inclui `Instalar_VinaLab.bat` e remove runtimes legados da pasta instalada.
- Interface desktop para AutoDock Vina com fluxo de conversão, configuração, docking, resultados, visualização 3D e relatórios.
- Conversão de ligantes PDB/MOL2 para PDBQT com validação de geometria via RDKit e fallback Meeko.
- Visualização 3D de receptor e pose de ligante em Py3Dmol/3Dmol.js.
- Tabelas de resultados, interações, clusters e consenso com tooltips em pt-BR.
- Layout responsivo validado para 1280x720, 1920x1080 e 2560x1440.
- Auditoria inicial de strings visíveis em pt-BR.
