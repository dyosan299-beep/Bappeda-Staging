{
  "brand_constraints": {
    "keep_existing_theme": true,
    "colors_locked": {
      "teal": "#117A69",
      "dark_teal": "#0B4F45",
      "navy": "#232F3E",
      "mint": "#6FE3CF",
      "amber": "#F4B63A"
    },
    "fonts_locked": {
      "heading": "font-head (existing)"
    },
    "scope_only": [
      "Floating Aksesibilitas button + panel",
      "Bottom-center caption bar",
      "Floating BISINDO video window",
      "Chart accessibility controls (summary + table toggle + speak button + table)",
      "SpeakMini buttons in card headers"
    ],
    "non_negotiables": [
      "Do NOT remove any data, feature, or behavior",
      "Keep all existing data-testid attributes; add missing ones using kebab-case role naming",
      "WCAG AA contrast, 44px touch targets, visible focus rings"
    ]
  },

  "design_intent": {
    "personality": ["professional", "rapih", "elegant", "government-grade", "accessibility-first"],
    "layout_principles": [
      "Reduce visual noise: fewer borders, more spacing",
      "Use consistent radii + shadows for hierarchy",
      "Prefer solid surfaces; gradients only as small accents (<=20% viewport)"
    ],
    "motion": {
      "rule": "No transition: all. Only transition-colors, shadow, opacity. Respect 'Kurangi animasi' by disabling motion classes when active.",
      "micro_interactions": [
        "Buttons: hover darken + subtle shadow lift",
        "Segmented controls: active pill slides (no transform transitions if reduced motion)",
        "Panel: subtle fade/scale-in (optional; disable when reduced motion)"
      ]
    }
  },

  "tokens_css_custom_properties": {
    "instructions": "Define these in a global CSS file (e.g., index.css) OR map to Tailwind via existing theme. Do not change theme colors; these are aliases for consistency.",
    "css": ":root{\n  --c-teal:#117A69;\n  --c-teal-900:#0B4F45;\n  --c-navy:#232F3E;\n  --c-mint:#6FE3CF;\n  --c-amber:#F4B63A;\n\n  --radius-lg:16px;\n  --radius-md:12px;\n  --radius-sm:10px;\n\n  --shadow-elev-1:0 10px 30px rgba(35,47,62,.14);\n  --shadow-elev-2:0 18px 50px rgba(35,47,62,.18);\n\n  --ring:0 0 0 3px rgba(111,227,207,.55);\n}\n"
  },

  "tailwind_recipes": {
    "floating_aksesibilitas_button": {
      "goal": "More premium + tidy: icon-only on mobile, icon+label on md+. 44px min target. No loud gradients.",
      "wrapper": "fixed bottom-4 right-4 z-50",
      "button": "group inline-flex items-center gap-2 rounded-full bg-[#117A69] text-white shadow-[0_14px_40px_rgba(17,122,105,.28)] ring-1 ring-white/15 px-4 py-3 min-h-11 min-w-11 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#6FE3CF]/60 hover:bg-[#0B4F45] transition-colors",
      "icon_circle": "grid place-items-center h-9 w-9 rounded-full bg-white/12 ring-1 ring-white/15",
      "label": "hidden md:inline text-sm font-semibold tracking-wide",
      "hint_badge_optional": "ml-1 hidden lg:inline-flex items-center rounded-full bg-white/12 px-2 py-0.5 text-[11px] font-medium ring-1 ring-white/15"
    },

    "aksesibilitas_panel_shell": {
      "panel": "fixed bottom-20 right-4 z-50 w-[min(420px,calc(100vw-2rem))] rounded-[16px] bg-white text-slate-900 shadow-[0_18px_60px_rgba(35,47,62,.22)] ring-1 ring-slate-200 overflow-hidden",
      "panel_inner": "flex flex-col",
      "header": "px-4 pt-4 pb-3 bg-[#232F3E] text-white",
      "header_top_row": "flex items-start justify-between gap-3",
      "title": "font-head text-base leading-6",
      "subtitle": "mt-0.5 text-xs text-white/80 leading-5",
      "close_button": "inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/10 hover:bg-white/15 ring-1 ring-white/15 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#6FE3CF]/60 transition-colors",
      "tabs_wrap": "px-4 pt-3 pb-4 bg-white",
      "tabs_segmented": "grid grid-cols-3 rounded-full bg-slate-100 p-1 ring-1 ring-slate-200",
      "tab": "inline-flex items-center justify-center rounded-full px-3 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#6FE3CF]/60 transition-colors",
      "tab_active": "bg-white text-slate-900 shadow-sm ring-1 ring-slate-200"
    },

    "panel_content_layout": {
      "section": "px-4 pb-4",
      "section_title": "text-xs font-semibold text-slate-700 tracking-wide",
      "card": "mt-2 rounded-[14px] bg-white ring-1 ring-slate-200 shadow-[0_10px_24px_rgba(35,47,62,.08)]",
      "card_body": "p-3",
      "divider": "my-3 h-px bg-slate-200"
    },

    "tampilan_tab_controls": {
      "text_size_cards_wrap": "mt-2 grid grid-cols-3 gap-2",
      "text_size_card": "rounded-[12px] bg-white ring-1 ring-slate-200 px-3 py-3 text-center hover:ring-slate-300 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#6FE3CF]/60 transition-colors",
      "text_size_card_active": "ring-2 ring-[#117A69]",
      "text_size_label": "font-head text-base",

      "toggle_tiles_wrap": "mt-3 grid grid-cols-2 gap-2",
      "toggle_tile": "rounded-[14px] bg-slate-50 ring-1 ring-slate-200 p-3 hover:bg-white transition-colors",
      "toggle_tile_top": "flex items-start justify-between gap-2",
      "toggle_tile_title": "text-sm font-semibold text-slate-900",
      "toggle_tile_desc": "mt-0.5 text-xs text-slate-600 leading-5",
      "status_badge_on": "inline-flex items-center rounded-full bg-[#117A69]/10 text-[#0B4F45] px-2 py-0.5 text-[11px] font-semibold ring-1 ring-[#117A69]/20",
      "status_badge_off": "inline-flex items-center rounded-full bg-slate-200/70 text-slate-700 px-2 py-0.5 text-[11px] font-semibold ring-1 ring-slate-300",

      "speech_rate_wrap": "mt-3",
      "speech_rate_row": "flex items-center justify-between gap-3",
      "speech_rate_label": "text-sm font-semibold text-slate-900",
      "try_voice_link": "text-xs font-semibold text-[#117A69] hover:text-[#0B4F45] underline underline-offset-4",
      "segmented": "mt-2 grid grid-cols-3 rounded-full bg-slate-100 p-1 ring-1 ring-slate-200",
      "segmented_item": "rounded-full px-3 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#6FE3CF]/60 transition-colors",
      "segmented_item_active": "bg-white text-slate-900 shadow-sm ring-1 ring-slate-200",

      "reset_button": "mt-3 inline-flex w-full items-center justify-center rounded-[12px] bg-white text-slate-900 ring-1 ring-slate-200 px-4 py-3 text-sm font-semibold hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#6FE3CF]/60 transition-colors"
    },

    "disabilitas_buta_tab_controls": {
      "primary_button": "inline-flex w-full items-center justify-center gap-2 rounded-[12px] bg-[#117A69] text-white px-4 py-3 text-sm font-semibold shadow-[0_12px_30px_rgba(17,122,105,.22)] hover:bg-[#0B4F45] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#6FE3CF]/60 transition-colors",
      "secondary_button": "inline-flex w-full items-center justify-center gap-2 rounded-[12px] bg-white text-slate-900 ring-1 ring-slate-200 px-4 py-3 text-sm font-semibold hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#6FE3CF]/60 transition-colors",
      "status_row": "mt-2 flex items-center gap-2 text-xs text-slate-700",
      "status_dot_on": "h-2.5 w-2.5 rounded-full bg-[#117A69] ring-2 ring-[#6FE3CF]/40",
      "status_dot_off": "h-2.5 w-2.5 rounded-full bg-slate-300",

      "section_list": "mt-3 space-y-2",
      "section_row": "flex items-center justify-between gap-3 rounded-[12px] bg-white ring-1 ring-slate-200 px-3 py-2.5 hover:ring-slate-300 transition-colors",
      "section_row_left": "min-w-0",
      "section_row_title": "text-sm font-semibold text-slate-900 truncate",
      "section_row_hint": "text-xs text-slate-600",
      "jump_label": "inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700 ring-1 ring-slate-200",
      "speaker_button": "inline-flex h-11 w-11 items-center justify-center rounded-full bg-white ring-1 ring-slate-200 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#6FE3CF]/60 transition-colors",

      "switch_row": "mt-2 flex items-center justify-between gap-3 rounded-[12px] bg-slate-50 ring-1 ring-slate-200 px-3 py-3",
      "switch_row_text": "min-w-0",
      "switch_row_title": "text-sm font-semibold text-slate-900",
      "switch_row_desc": "mt-0.5 text-xs text-slate-600 leading-5",
      "link_row": "mt-2 flex items-center justify-between gap-3 rounded-[12px] bg-white ring-1 ring-slate-200 px-3 py-3 hover:bg-slate-50 transition-colors",
      "link_row_right": "text-xs font-semibold text-[#117A69]"
    },

    "disabilitas_tuli_tab_controls": {
      "switch_row": "flex items-center justify-between gap-3 rounded-[12px] bg-slate-50 ring-1 ring-slate-200 px-3 py-3",
      "transcript_row": "mt-2 flex items-center justify-between gap-3 rounded-[12px] bg-white ring-1 ring-slate-200 px-3 py-3",
      "subtitle_example_box": "mt-2 rounded-[12px] bg-slate-900 text-white px-3 py-3 text-sm leading-6 shadow-[0_12px_30px_rgba(35,47,62,.18)]",
      "subtitle_example_label": "text-xs text-white/70",
      "subtitle_example_text": "mt-1 font-medium"
    },

    "panel_footer": {
      "footer": "px-4 py-3 bg-slate-50 ring-1 ring-slate-200/60",
      "kbd_row": "flex flex-wrap items-center gap-2 text-xs text-slate-700",
      "kbd": "inline-flex items-center rounded-md bg-white px-2 py-1 font-mono text-[11px] ring-1 ring-slate-200"
    },

    "bottom_center_caption_bar": {
      "bar": "fixed bottom-4 left-1/2 -translate-x-1/2 z-40 w-[min(720px,calc(100vw-2rem))] rounded-[14px] bg-slate-950 text-white shadow-[0_18px_60px_rgba(0,0,0,.35)] ring-1 ring-white/10 px-4 py-3",
      "text": "text-base sm:text-lg font-semibold leading-6",
      "meta_row_optional": "mt-1 flex items-center justify-between text-xs text-white/70"
    },

    "bisindo_floating_window": {
      "window": "fixed bottom-20 left-4 z-40 w-[min(360px,calc(100vw-2rem))] rounded-[16px] bg-white shadow-[0_18px_60px_rgba(35,47,62,.22)] ring-1 ring-slate-200 overflow-hidden",
      "header": "px-3 py-2 bg-[#232F3E] text-white flex items-center justify-between",
      "title": "text-sm font-semibold",
      "controls": "flex items-center gap-1",
      "icon_button": "inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/10 hover:bg-white/15 ring-1 ring-white/15 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#6FE3CF]/60 transition-colors",
      "video_area": "bg-black aspect-video",
      "note": "Replace current purple header with navy (#232F3E) to stay on-theme; do not change behavior."
    },

    "chart_accessibility_block": {
      "wrap": "mt-3 rounded-[14px] bg-slate-50 ring-1 ring-slate-200 p-3",
      "label": "text-xs font-semibold text-slate-700",
      "summary": "mt-1 text-sm text-slate-800 leading-6",
      "actions": "mt-3 flex items-center gap-2",
      "table_toggle_button": "inline-flex items-center gap-2 rounded-[12px] bg-white text-slate-900 ring-1 ring-slate-200 px-3 py-2.5 text-sm font-semibold hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#6FE3CF]/60 transition-colors",
      "speak_mini_button": "inline-flex h-11 w-11 items-center justify-center rounded-full bg-white text-[#117A69] ring-1 ring-slate-200 hover:bg-slate-50 hover:text-[#0B4F45] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#6FE3CF]/60 transition-colors",
      "table_wrap": "mt-3 overflow-hidden rounded-[14px] bg-white ring-1 ring-slate-200",
      "table": "w-full text-left text-sm",
      "thead": "bg-slate-50 text-xs font-semibold text-slate-700",
      "th": "px-3 py-2",
      "tr": "border-t border-slate-200",
      "td": "px-3 py-2 text-slate-800",
      "zebra": "odd:bg-white even:bg-slate-50/60",
      "table_scroll": "max-h-64 overflow-auto"
    },

    "speakmini_in_card_headers": {
      "button": "inline-flex h-10 w-10 items-center justify-center rounded-full bg-white text-[#117A69] ring-1 ring-slate-200 hover:bg-slate-50 hover:text-[#0B4F45] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#6FE3CF]/60 transition-colors",
      "placement": "Use consistent spacing: place at far-right of header row with gap-2 from other actions."
    }
  },

  "data_testid_rules": {
    "keep_existing": true,
    "add_if_missing_examples": {
      "floating_button": "data-testid=\"aksesibilitas-fab-button\"",
      "panel": "data-testid=\"aksesibilitas-panel\"",
      "tab_tampilan": "data-testid=\"aksesibilitas-tab-tampilan\"",
      "tab_disabilitas_buta": "data-testid=\"aksesibilitas-tab-tunanetra\"",
      "tab_disabilitas_tuli": "data-testid=\"aksesibilitas-tab-tunarungu\"",
      "table_toggle": "data-testid=\"chart-data-table-toggle-button\"",
      "speak_button": "data-testid=\"chart-summary-speak-button\""
    },
    "convention": "kebab-case; describe role not appearance"
  },

  "component_path": {
    "shadcn_primary": [
      "/app/frontend/src/components/ui/button.js",
      "/app/frontend/src/components/ui/tabs.js",
      "/app/frontend/src/components/ui/switch.js",
      "/app/frontend/src/components/ui/separator.js",
      "/app/frontend/src/components/ui/badge.js",
      "/app/frontend/src/components/ui/tooltip.js"
    ],
    "note": "Use existing shadcn primitives where already used; otherwise apply Tailwind recipes above directly in current components (JS files)."
  },

  "instructions_to_main_agent": [
    "Do not change theme colors; only adjust layout, spacing, radii, shadows, and states using the Tailwind recipes.",
    "Ensure all interactive elements meet 44px min touch target (use h-11/w-11 or py-3).",
    "Do not introduce new gradients; keep header solid navy (#232F3E).",
    "Avoid 'transition-all'. Use 'transition-colors' (and optionally 'shadow'/'opacity') only.",
    "Keep existing data-testids; if any element lacks one, add per rules above without renaming existing.",
    "Caption bar: keep black surface but refine radius/shadow and typography per recipe.",
    "BISINDO window: change header from purple to navy to match theme; keep video behavior unchanged.",
    "Chart block: group summary + actions into a subtle slate-50 container; make speak button consistent with other icon buttons."
  ],

  "image_urls": [],

  "general_ui_ux_design_guidelines_appendix": "<General UI UX Design Guidelines>  \n    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms\n    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text\n   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json\n\n **GRADIENT RESTRICTION RULE**\nNEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc\nNEVER use dark gradients for logo, testimonial, footer etc\nNEVER let gradients cover more than 20% of the viewport.\nNEVER apply gradients to text-heavy content or reading areas.\nNEVER use gradients on small UI elements (<100px width).\nNEVER stack multiple gradient layers in the same viewport.\n\n**ENFORCEMENT RULE:**\n    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors\n\n**How and where to use:**\n   • Section backgrounds (not content backgrounds)\n   • Hero section header content. Eg: dark to light to dark color\n   • Decorative overlays and accent elements only\n   • Hero section with 2-3 mild color\n   • Gradients creation can be done for any angle say horizontal, vertical or diagonal\n\n- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**\n\n</Font Guidelines>\n\n- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. \n   \n- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.\n\n- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.\n   \n- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly\n    Eg: - if it implies playful/energetic, choose a colorful scheme\n           - if it implies monochrome/minimal, choose a black–white/neutral scheme\n\n**Component Reuse:**\n\t- Prioritize using pre-existing components from src/components/ui when applicable\n\t- Create new components that match the style and conventions of existing components when needed\n\t- Examine existing components to understand the project's component patterns before creating new ones\n\n**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component\n\n**Best Practices:**\n\t- Use Shadcn/UI as the primary component library for consistency and accessibility\n\t- Import path: ./components/[component-name]\n\n**Export Conventions:**\n\t- Components MUST use named exports (export const ComponentName = ...)\n\t- Pages MUST use default exports (export default function PageName() {...})\n\n**Toasts:**\n  - Use `sonner` for toasts\"\n  - Sonner component are located in `/app/src/components/ui/sonner.tsx`\n\nUse 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.\n</General UI UX Design Guidelines>"
}
