# Offline Three.js Viewer

Three.js r160 and OrbitControls are bundled unmodified from the official repository.
Release tag object: `643680ed5fc73ba27e32a6529d59cae8c8b3825c`.
Resolved commit: `d04539a76736ff500cae883d6a38b3dd8643c548`.
The release tag was verified against the GitHub Git References/Tags API.

Source base: https://raw.githubusercontent.com/mrdoob/three.js/d04539a76736ff500cae883d6a38b3dd8643c548/

| Local file | Upstream path | SHA-256 |
| --- | --- | --- |
| three.module.js | build/three.module.js | 76dea8151bc9352aef3528b4262e249b2604f62543828328db978d060d61a495 |
| OrbitControls.js | examples/jsm/controls/OrbitControls.js | 5a44a9e86a2a0fb11933eed69bc2cd33c76a496854c1aed6ed776efa87d7b064 |
| LICENSE | LICENSE | 852e0e8699169bf9f6fdc6bda3e682d078dcbc738b5d33e74df594721bff271d |

No CDN, server, remote font, or network API is used at runtime. Qt additionally
blocks requests outside this asset directory. Bundle this entire directory at
`vinalab_ui/widgets/assets/box_viewer` in wheels and frozen distributions.

Molecules are coordinate-only atom markers, not inferred chemical bonds or surfaces.
