# VinaLab v0.0.6

## Melhorias de Interface e Usabilidade

### Design Modernizado
- Tema claro profissional com paleta de cores coerente (Canvas #eef1f6, Accent #2f6fed)
- Tipografia e espaçamento recalibrados para hierarquia visual clara
- Botões, campos e painéis com aparência consistente e polida

### Barras de Rolagem Draggáveis
- Barras de rolagem horizontal e vertical visíveis e arrastáveis em todos os painéis laterais
- Handle escuro (#5b6573) sobre fundo (#dde3ec) com alto contraste
- Espessura de 17px para fácil interação com o mouse
- Hover e pressed states com destaque em azul

### Proteção Contra Alteração Acidental de Parâmetros
- Rolar a roda do mouse sobre spinboxes e comboboxes agora move o painel em vez de alterar o valor
- Valores ainda podem ser ajustados clicando e digitando ou usando os botões ↑↓
- Elimina problema de parâmetros alterados sem intenção durante navegação

### Outros
- Handles do splitter redesenhados para não serem confundidos com barras de rolagem
- Arquivos de diagnóstico temporários removidos do repositório

## Correções

- Empacotamento corrigido para que o app abra em qualquer computador: DLLs do
  PySide6/Qt6 e o runtime do Microsoft Visual C++ agora viajam no executável
  (resolve o erro "DLL load failed" / DLL ausente em máquinas limpas)
- Corrigido travamento na abertura (KeyError em verificação de dependências)
- Conversão de receptor para PDBQT agora funciona no app empacotado: usa o Meeko
  (mk_prepare_receptor) em processo, com Open Babel como alternativa, sem depender
  de ferramentas de linha de comando externas. O Open Babel também passa a ser
  empacotado para a conversão de receptores e arquivos MOL2
