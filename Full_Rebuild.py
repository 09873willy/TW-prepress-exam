import pdfplumber
import re
import json
import os
import sys
import codecs

# 強制 UTF-8 輸出以預防 Windows 終端機亂碼
if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def clean_pdf_text(text):
    if not text: return ""
    # 移除頁碼干擾
    text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'第\s*\d+\s*頁(?:[ /共]+)?(?:\d+\s*頁)?', '', text)
    # 移除中文字元之間被錯誤插入的空格
    text = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', text)
    text = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', text)
    
    # 修復英文單字被 PDF 錯誤插入空格的問題 (針對印前製程常見軟體與專有名詞)
    fix_words = ["Photoshop", "Illustrator", "InDesign", "Acrobat", "PANTONE", "CMYK", "RGB", "EPS", "TIFF", "JPEG", "Mac", "Windows", "solid", "coated", "uncoated", "matte", "process", "guide"]
    for w in fix_words:
        pattern = r'\b' + r'\s?'.join(list(w)) + r'\b'
        text = re.sub(pattern, w, text, flags=re.IGNORECASE)

    return text

# --- 專業與共同科目知識庫 (擴充版) ---
SPECIFIC_LOGIC = {
    "缺水": "【台灣缺水原因】：1. 地形陡峻降雨迅速入海。 2. 地域季節分布不均。 3. 人口密度高，人均降雨量少。注意：『水價便宜』非自然地理缺水主因。",
    "菊八開": "【台數計算】：菊全開(G1K)面積為菊八開(G8K)的8倍。正反印刷1張大紙可印16頁。公式：總頁數 ÷ 16 = 總台數。",
    "菊全開": "【紙張規格】：菊全開 (G1K) 是常用的印刷大紙，尺寸約為 25 x 35 英吋 (635 x 889 mm)。",
    "四六版": "【紙張規格】：四六版 (B1) 尺寸約為 31 x 43 英吋 (787 x 1092 mm)，通常用於海報或大尺寸印刷。",
    "穿線膠裝": "【裝訂工藝】：穿線膠裝 (Smyth Sewn) 是將書帖先以線縫合再上膠，耐翻且可平攤，適合精裝書或厚書。",
    "騎馬釘": "【裝訂工藝】：騎馬釘 (Saddle Stitching) 使用金屬線釘在書脊上，適合頁數較少（通常 64 頁以內）的型錄。",
    "膠裝": "【裝訂工藝】：平裝/膠裝 (Perfect Binding) 將書頁邊緣銑溝後上膠與封面黏合，是最常見的書籍裝訂方式。",
    "嵌入": "【圖檔處理】：『嵌入 (Embed)』會將原始圖檔資料存入排版檔，導致檔案肥大；『連結 (Link)』則僅儲存路徑，有利協作與保持檔案輕巧。",
    "液態版面": "【InDesign】：『液態版面 (Liquid Layout)』可設定物件隨頁面尺寸縮放的規則，快速產出不同尺寸設計。",
    "出血": "【印刷規範】：『出血 (Bleed)』通常設定為 3mm，預防裁切誤差導致成品邊緣出現白邊。",
    "解析度": "【解析度準則】：印刷圖檔 PPI 應為網屏線數 LPI 的 2 倍。例如 175 LPI 印刷需 350 PPI 圖檔。螢幕顯示通常為 72 PPI。",
    "PDF/X": "【PDF 標準】：PDF/X-1a (僅 CMYK/無透明度)、PDF/X-3 (支援色彩管理)、PDF/X-4 (支援透明度)，是印刷標準格式。",
    "RGB": "【色彩模式】：RGB 為光的三原色 (紅綠藍)，屬於加色法，混合為白色，適用於螢幕顯示。",
    "CMYK": "【色彩模式】：CMYK 為印刷四分色 (青洋紅黃黑)，屬於減色法，混合為深褐色 (需加 K 墨)，適用於印刷。",
    "網點": "【印刷網點】：AM (調幅) 改變網點大小來表現濃淡，FM (調頻) 改變網點分佈密度。",
    "陷印": "【印前補漏白】：陷印 (Trapping) 是為了防止印刷套印不準，而在相鄰不同顏色邊緣做微小的重疊處理。",
    "直壓": "【印前疊印】：直壓 (Overprint) 讓上層顏色直接印在下層顏色上，通常用於黑色文字 (K100) 以避免漏白。",
    "PANTONE": "【色彩對比】：比對 PANTONE 純色(特別色)與其最接近的 CMYK 印刷色時，應使用『PANTONE solid to process guide (特別色對照四色演色指南)』。",
    "童工": "【勞基法】：15歲以上未滿16歲為童工。每日工時不得超過8小時，不得於午後8時至翌晨6時工作，例假日不得工作。",
    "特別休假": "【勞基法】：勞工繼續工作滿一定期間，雇主應給予特別休假。滿半年有3天，滿1年有7天。",
    "性騷擾": "【性別工作平等法】：雇主應防治性騷擾發生，發生時應採取立即有效之糾正及補救措施。",
    "溫室氣體": "【環境保護】：主要溫室氣體包含二氧化碳 (CO2)、甲烷 (CH4)、氧化亞氮 (N2O)，會造成全球暖化。",
    "回收": "【資源回收】：常見回收標誌為四個箭頭組成的方形。落實分類可減少垃圾量並促進資源循環利用。",
    "著作權": "【智慧財產權】：著作權自創作完成時即自動產生，不需登記。包含著作人格權與著作財產權。",
    "個資": "【個人資料保護】：蒐集、處理或利用個人資料，應尊重當事人之權益，並依誠實及信用方法為之。",
    "職業災害": "【職安法規】：勞工因就業場所之設備、化學品等或作業活動引起之疾病、傷害、失能或死亡。"
}

SUBJECT_HINTS = {
    "90006": "【職業安全提示】：本題測驗工作環境安全、危害辨識及勞工權益保障之基礎觀念。",
    "90007": "【工作倫理提示】：本題測驗職場誠實、保密義務、法規遵循及專業道德守則。",
    "90008": "【環境保護提示】：本題測驗污染防治、資源回收、毒性物質處理及生態永續發展。",
    "90009": "【節能減碳提示】：本題測驗低碳能源推廣、排碳量計算及節能標章產品之認知。"
}

COMMON_WORDS = {
    "Signature": "台/書帖", "Bleed": "出血", "G1K": "菊全開", "G8K": "菊八開",
    "Smyth Sewn": "穿線膠裝", "Embed": "嵌入", "Link": "連結",
    "Liquid Layout": "液態版面", "Alternate Layout": "替代版面",
    "LPI": "網屏線數", "PPI": "像素解析度", "DPI": "輸出解析度",
    "CMYK": "印刷四分色", "RGB": "螢幕三原色", "PDF/X-1a": "印刷標準(無透明度)",
    "PDF/X-3": "印刷標準(支援色彩管理)", "PDF/X-4": "印刷標準(支援透明度)",
    "RIP": "光柵影像處理器", "CTP": "電腦直接製版", "PDF": "可攜式文件格式",
    "EPS": "封裝PostScript", "TIFF": "標籤影像檔案格式", "JPEG": "聯合攝影專家群",
    "CIP3": "印前中後整合", "CIP4": "印前中後整合(含JDF)",
    "JDF": "工作定義格式", "OPI": "印前開放介面", "CMS": "色彩管理系統",
    "ICC": "國際色彩聯盟", "InDesign": "專業排版軟體", "Illustrator": "向量繪圖軟體",
    "Photoshop": "影像處理軟體", "Acrobat": "PDF編輯軟體", "PostScript": "頁面描述語言",
    "Mac OS": "蘋果作業系統", "Windows": "微軟作業系統", "RAM": "隨機存取記憶體",
    "ROM": "唯讀記憶體", "CPU": "中央處理器", "GPU": "圖形處理器",
    "SSD": "固態硬碟", "HDD": "傳統硬碟", "USB": "通用序列匯流排",
    "LAN": "區域網路", "WAN": "廣域網路", "WLAN": "無線區域網路",
    "FTP": "檔案傳輸協定", "HTTP": "超文本傳輸協定", "URL": "統一資源定位器",
    "QR Code": "快速響應矩陣碼", "Barcode": "條碼", "RFID": "無線射頻辨識",
    "UI": "使用者介面", "UX": "使用者體驗", "App": "應用程式",
    "PANTONE": "國際標準色卡", "solid coated": "光面銅版紙", "solid uncoated": "霧面模造紙",
    "matte": "雪銅紙", "process guide": "四色演色指南"
}

def extract_glossary(text):
    """精準提取英文術語並避免誤判"""
    found_terms = []
    # 使用負向預查與後顧，確保提取的是完整單字，不會把 Space 裡的 PC 抓出來
    for key, zh in COMMON_WORDS.items():
        pattern = r'(?<![A-Za-z])' + re.escape(key) + r'(?![A-Za-z])'
        if re.search(pattern, text, re.IGNORECASE):
            found_terms.append(f"📌 <b>{key}</b>：{zh}")
    return found_terms

def get_enhanced_explanation(combined_text, group_code):
    """根據題目與選項內容，動態組合出獨立的解析"""
    exps = []
    for key, value in SPECIFIC_LOGIC.items():
        if key in combined_text:
            exps.append(value)
    
    if not exps:
        exps.append(SUBJECT_HINTS.get(group_code, "【基礎解析】：請參考官方題庫標準答案與相關專業知識。"))
    
    return "<br><br>".join(exps)

def parse_pdf(pdf_path, group_code, group_name):
    questions = []
    print(f">>> Processing: {os.path.basename(pdf_path)}")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += clean_pdf_text(page_text) + "\n"
        
        pattern = re.compile(r'(\d+)\.\s*\(([\d\s,]+)\)\s*(.*?)(?=\n\d+\.\s*\(|$)', re.DOTALL)
        matches = pattern.finditer(full_text)
        
        for match in matches:
            q_id = match.group(1)
            raw_ans = match.group(2).strip()
            content = match.group(3).strip()
            
            is_multiple = ',' in raw_ans or len(raw_ans.replace(' ', '')) > 1
            correct_indices = []
            if ',' in raw_ans:
                correct_indices = [int(a.strip()) - 1 for a in raw_ans.split(',') if a.strip()]
            else:
                correct_indices = [int(a) - 1 for a in raw_ans.replace(' ', '') if a.isdigit()]
            
            opt_markers = ['①', '②', '③', '④']
            first_opt = len(content)
            for m in opt_markers:
                idx = content.find(m)
                if idx != -1 and idx < first_opt: first_opt = idx
            
            title = content[:first_opt].strip()
            opts_raw = [o.strip() for o in re.split(r'[①②③④]', content[first_opt:]) if o.strip()]
            options = opts_raw[:4]
            
            # 動態組合解析
            combined_text = title + " " + " ".join(options)
            exp_html = get_enhanced_explanation(combined_text, group_code)
            
            # 提取術語字典
            title_glossary = extract_glossary(title)
            opts_glossary = []
            for opt in options: opts_glossary.extend(extract_glossary(opt))
            exp_glossary = extract_glossary(exp_html)
            
            full_glossary = list(dict.fromkeys(title_glossary + opts_glossary + exp_glossary))
            
            # 標記否定詞 (僅用於前端顯示)
            title_html = re.sub(r'(不|非|錯誤|誤|不正確)', r'<u>\1</u>', title)

            questions.append({
                "id": f"{group_code}_{q_id}",
                "originalNum": q_id,
                "group": group_name,
                "type": "複選" if is_multiple else "單選",
                "title": title_html,
                "options": options,
                "correct": correct_indices,
                "explanation": exp_html,
                "glossary": "<br>".join(full_glossary)
            })
    except Exception as e:
        print(f"Error parsing {pdf_path}: {e}")
    return questions

def main():
    user_home = os.environ['USERPROFILE']
    downloads = os.path.join(user_home, "Downloads")
    desktop = os.path.join(user_home, "Desktop")
    
    all_questions = []
    
    p19100 = next((f for f in os.listdir(downloads) if "19100" in f and f.endswith(".pdf")), None)
    if p19100:
        all_questions.extend(parse_pdf(os.path.join(downloads, p19100), "19100", "專業科目 · 印前製程乙級"))
    
    common_codes = {"90006": "共同科目 · 職業安全", "90007": "共同科目 · 工作倫理", "90008": "共同科目 · 環境保護", "90009": "共同科目 · 節能減碳"}
    for code, name in common_codes.items():
        p_common = next((f for f in os.listdir(downloads) if code in f and f.endswith(".pdf")), None)
        if p_common:
            all_questions.extend(parse_pdf(os.path.join(downloads, p_common), code, name))

    if not all_questions:
        print("❌ No PDF files found in Downloads folder.")
        return

    html_content = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>乙級製程與共同科目全題庫解析</title>
    <style>
        :root { --primary: #2563eb; --success: #16a34a; --bg: #f8fafc; --text: #1e293b; }
        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body { font-family: -apple-system, "Microsoft JhengHei", sans-serif; background: var(--bg); color: var(--text); margin: 0; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        
        #app { flex: 1; display: flex; flex-direction: column; padding: 20px; max-width: 800px; margin: 0 auto; width: 100%; overflow-y: auto; scroll-behavior: smooth; }
        .card { background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); margin-bottom: 80px; }
        
        .badge { display: inline-block; padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 600; margin-bottom: 12px; }
        .badge-group { background: #dbeafe; color: #1e40af; }
        .badge-type { background: #fef2f2; color: #991b1b; margin-left: 8px; }
        .badge-learned { background: #dcfce7; color: #166534; float: right; }

        .question-title { font-size: clamp(1.2rem, 4vw, 1.8rem); line-height: 1.5; font-weight: 700; margin: 20px 0; }
        .options-list { display: grid; gap: 12px; margin: 25px 0; }
        .option-item { padding: 16px; border: 2px solid #e2e8f0; border-radius: 12px; cursor: pointer; transition: all 0.2s; font-size: 1.1rem; display: flex; align-items: center; }
        .option-item:hover { border-color: var(--primary); background: #eff6ff; }
        .option-item.correct { border-color: var(--success); background: #f0fdf4; color: var(--success); font-weight: 600; }
        .option-item.wrong { border-color: #ef4444; background: #fef2f2; color: #b91c1c; }
        
        .explanation-box { margin-top: 30px; padding: 20px; background: #f1f5f9; border-radius: 12px; display: none; }
        .exp-header { font-weight: 700; color: #475569; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
        .glossary-box { margin-top: 15px; border-top: 1px solid #cbd5e1; padding-top: 15px; font-size: 0.95rem; color: #64748b; line-height: 1.6; }

        .controls { position: fixed; bottom: 0; left: 0; right: 0; background: white; border-top: 1px solid #e2e8f0; padding: 15px; transition: transform 0.3s; z-index: 100; }
        .controls.hidden { transform: translateY(100%); }
        .control-inner { max-width: 800px; margin: 0 auto; display: flex; justify-content: space-between; align-items: center; }
        
        .nav-group { display: flex; align-items: center; gap: 10px; }
        .nav-btn { padding: 10px 20px; border-radius: 8px; border: 1px solid #e2e8f0; background: white; cursor: pointer; font-weight: 600; }
        .nav-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        
        .page-info { font-weight: 600; color: #64748b; cursor: pointer; padding: 8px 16px; border-radius: 8px; transition: background 0.2s; display: flex; align-items: center; gap: 8px; }
        .page-info:hover { background: #f1f5f9; }
        
        .settings-btn { cursor: pointer; padding: 8px 12px; border-radius: 8px; border: 1px solid #e2e8f0; background: #f8fafc; font-weight: 600; color: #475569; display: flex; align-items: center; gap: 6px; transition: background 0.2s; }
        .settings-btn:hover { background: #e2e8f0; }

        .toggle-arrow { position: absolute; top: -25px; left: 50%; transform: translateX(-50%); background: white; border: 1px solid #e2e8f0; border-bottom: none; border-radius: 8px 8px 0 0; width: 50px; height: 25px; cursor: pointer; display: flex; align-items: center; justify-content: center; color: #94a3b8; transition: color 0.2s; }

        .modal { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: none; z-index: 200; align-items: center; justify-content: center; padding: 20px; }
        .modal-content { background: white; border-radius: 16px; width: 100%; max-width: 500px; max-height: 80vh; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; }
        .modal-item { padding: 12px; border-bottom: 1px solid #f1f5f9; cursor: pointer; }
        .modal-item:hover { background: #f8fafc; }
        .modal-item.learned { border-left: 4px solid var(--success); color: var(--success); }

        .shortcut-hint { 
            position: fixed; top: 10px; right: 10px; font-size: 11px; color: #94a3b8; 
            text-align: right; background: rgba(255,255,255,0.8); padding: 5px 10px; 
            border-radius: 6px; pointer-events: none;
            transition: opacity 0.3s, transform 0.3s;
            z-index: 150;
        }
        .shortcut-hint.hidden { opacity: 0; transform: translateY(-10px); }
        u { text-decoration-color: #ef4444; text-decoration-thickness: 2px; }
    </style>
</head>
<body>
    <div id="app">
        <div class="card">
            <div id="badge-container"></div>
            <div id="question-text" class="question-title">載入中...</div>
            <div id="options-container" class="options-list"></div>
            <div id="explanation" class="explanation-box">
                <div class="exp-header">💡 詳解分析</div>
                <div id="exp-text"></div>
                <div id="glossary" class="glossary-box"></div>
            </div>
        </div>
    </div>

    <div id="shortcut-hint" class="shortcut-hint">
        ⬅️➡️ 切換題目<br>
        Enter 標記：記錄至已學會，該題變綠，且僅在您按切換題目時才會移至列表末尾<br>
        空白鍵：隱藏選單與提示 · 1-4 鍵：快速答題 · ↑↓：捲動頁面
    </div>

    <div id="controls" class="controls">
        <div class="toggle-arrow" onclick="toggleControls()">▲</div>
        <div class="control-inner">
            <div class="nav-group">
                <button class="nav-btn" onclick="prev()">上一題</button>
                <button class="settings-btn" onclick="showSettingsModal()">⚙️設定</button>
            </div>
            
            <div class="page-info" onclick="showListModal()" title="點擊開啟選題清單">
                <span id="current-index">0</span> / <span id="total-count">0</span> 
                <span style="font-size:0.8rem; margin-left:4px;">▼</span>
            </div>
            
            <div class="nav-group">
                <button class="nav-btn" onclick="next()">下一題</button>
            </div>
        </div>
    </div>

    <!-- 選題清單 Modal -->
    <div id="list-modal" class="modal" onclick="closeModal(event, 'list-modal')">
        <div class="modal-content" onclick="event.stopPropagation()">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">
                <h3 style="margin: 0;">📑 選擇題目</h3>
                <button onclick="closeModal(event, 'list-modal')" style="border:none; background:none; font-size:1.5rem; cursor:pointer; color: #64748b;">×</button>
            </div>
            <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                <select id="filter-group" onchange="renderModalList()" style="flex: 2; padding: 8px; border-radius: 8px; border: 1px solid #e2e8f0; outline: none;">
                    <option value="all">所有科目章節</option>
                </select>
                <input type="number" id="filter-num" oninput="renderModalList()" placeholder="搜尋題號..." style="flex: 1; padding: 8px; border-radius: 8px; border: 1px solid #e2e8f0; outline: none;">
            </div>
            <div id="modal-list" style="overflow-y: auto; flex: 1;"></div>
        </div>
    </div>

    <!-- 設定 Modal -->
    <div id="settings-modal" class="modal" onclick="closeModal(event, 'settings-modal')">
        <div class="modal-content" style="max-width: 400px;" onclick="event.stopPropagation()">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">
                <h3 style="margin: 0;">⚙️ 系統設定</h3>
                <button onclick="closeModal(event, 'settings-modal')" style="border:none; background:none; font-size:1.5rem; cursor:pointer; color: #64748b;">×</button>
            </div>
            
            <div style="padding: 15px; background: #f8fafc; border-radius: 8px;">
                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; font-weight: 600; margin-bottom: 20px;">
                    <input type="checkbox" id="chk-opt" style="width: 20px; height: 20px;" onchange="toggleConfig('shuffleOpts', this.checked)"> 
                    <span style="font-size: 1.1rem;">打亂選項 (1234 隨機排列)</span>
                </label>
                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer; font-weight: 600;">
                    <input type="checkbox" id="chk-qs" style="width: 20px; height: 20px;" onchange="toggleConfig('shuffleQs', this.checked)"> 
                    <span style="font-size: 1.1rem;">打亂題目順序 (隨機抽題)</span>
                </label>
                <div style="font-size: 0.9rem; color: #ef4444; margin-top: 20px; padding-top: 15px; border-top: 1px dashed #cbd5e1;">
                    ⚠️ 變更設定後將自動重新整理頁面，並套用新的隨機排序。
                </div>
            </div>
        </div>
    </div>

    <script>
        const rawQuestions = __DATA__;
        let questions = JSON.parse(JSON.stringify(rawQuestions));
        let learnedSet = new Set(JSON.parse(localStorage.getItem('learned_19100_merged') || '[]'));
        let config = JSON.parse(localStorage.getItem('exam_config') || '{"shuffleOpts": true, "shuffleQs": false}');
        let displayOrder = Array.from({length: questions.length}, (_, i) => i);
        let currentIndex = 0;
        let isPanelHidden = false;
        let selectedOptions = new Set();

        function shuffleArray(array) {
            for (let i = array.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [array[i], array[j]] = [array[j], array[i]];
            }
            return array;
        }

        function initQuestions() {
            if (config.shuffleOpts) {
                questions.forEach(q => {
                    let optObjects = q.options.map((text, idx) => ({ text, originalIdx: idx }));
                    shuffleArray(optObjects);
                    q.options = optObjects.map(obj => obj.text);
                    q.correct = optObjects
                        .map((obj, newIdx) => q.correct.includes(obj.originalIdx) ? newIdx : -1)
                        .filter(idx => idx !== -1);
                });
            }
            if (config.shuffleQs) {
                shuffleArray(displayOrder);
            }
        }

        function toggleConfig(key, value) {
            config[key] = value;
            localStorage.setItem('exam_config', JSON.stringify(config));
            location.reload();
        }

        function syncOrder() {
            const learned = displayOrder.filter(i => learnedSet.has(questions[i].id));
            const unlearned = displayOrder.filter(i => !learnedSet.has(questions[i].id));
            displayOrder = [...unlearned, ...learned];
        }

        function toggleControls() {
            isPanelHidden = !isPanelHidden;
            const controls = document.getElementById('controls');
            const hint = document.getElementById('shortcut-hint');
            const arrow = document.querySelector('.toggle-arrow');
            
            controls.classList.toggle('hidden', isPanelHidden);
            hint.classList.toggle('hidden', isPanelHidden);
            
            arrow.innerHTML = isPanelHidden ? '▼' : '▲';
        }

        function render() {
            if (!questions || questions.length === 0) {
                document.getElementById('question-text').innerHTML = "題庫載入失敗或無資料。";
                return;
            }
            selectedOptions.clear();
            const q = questions[displayOrder[currentIndex]];
            const isLearned = learnedSet.has(q.id);
            
            document.getElementById('badge-container').innerHTML = `
                <span class="badge badge-group">${q.group}</span>
                <span class="badge badge-type">${q.type}</span>
                ${isLearned ? '<span class="badge badge-learned">✓ 已學會</span>' : ''}
            `;
            
            document.getElementById('question-text').innerHTML = q.title;
            const optContainer = document.getElementById('options-container');
            optContainer.innerHTML = '';
            
            q.options.forEach((opt, i) => {
                const div = document.createElement('div');
                div.className = 'option-item';
                div.innerHTML = `${i+1}. ${opt}`;
                div.onclick = () => checkAnswer(i);
                optContainer.appendChild(div);
            });

            document.getElementById('explanation').style.display = 'none';
            document.getElementById('current-index').innerText = currentIndex + 1;
            document.getElementById('total-count').innerText = questions.length;
            document.getElementById('app').scrollTop = 0;
        }

        function checkAnswer(idx) {
            const q = questions[displayOrder[currentIndex]];
            const items = document.querySelectorAll('.option-item');
            const isCorrect = q.correct.includes(idx);
            
            if (q.type === '單選') {
                items[idx].classList.add(isCorrect ? 'correct' : 'wrong');
                if (isCorrect) {
                    document.getElementById('explanation').style.display = 'block';
                    document.getElementById('exp-text').innerHTML = q.explanation;
                    
                    const glossaryBox = document.getElementById('glossary');
                    if (q.glossary && q.glossary.trim() !== '') {
                        glossaryBox.innerHTML = '<div style="font-weight:700; margin-bottom:10px; color:#1e40af;">📖 專有名詞與重點補充：</div>' + q.glossary;
                        glossaryBox.style.display = 'block';
                    } else {
                        glossaryBox.style.display = 'none';
                    }
                    
                    q.correct.forEach(cIdx => items[cIdx].classList.add('correct'));
                }
            } else {
                // 複選
                if (isCorrect) {
                    items[idx].classList.add('correct');
                    selectedOptions.add(idx);
                } else {
                    items[idx].classList.add('wrong');
                }
                
                const allCorrectSelected = q.correct.every(c => selectedOptions.has(c));
                if (allCorrectSelected) {
                    document.getElementById('explanation').style.display = 'block';
                    document.getElementById('exp-text').innerHTML = q.explanation;
                    
                    const glossaryBox = document.getElementById('glossary');
                    if (q.glossary && q.glossary.trim() !== '') {
                        glossaryBox.innerHTML = '<div style="font-weight:700; margin-bottom:10px; color:#1e40af;">📖 專有名詞與重點補充：</div>' + q.glossary;
                        glossaryBox.style.display = 'block';
                    } else {
                        glossaryBox.style.display = 'none';
                    }
                    
                    q.correct.forEach(cIdx => items[cIdx].classList.add('correct'));
                }
            }
        }

        function markLearned() {
            const q = questions[displayOrder[currentIndex]];
            if (learnedSet.has(q.id)) {
                learnedSet.delete(q.id);
            } else {
                learnedSet.add(q.id);
            }
            localStorage.setItem('learned_19100_merged', JSON.stringify([...learnedSet]));
            render();
        }

        function next() {
            if (currentIndex < questions.length - 1) {
                syncOrder();
                currentIndex++;
                render();
            }
        }

        function prev() {
            if (currentIndex > 0) {
                currentIndex--;
                render();
            }
        }

        function showListModal() {
            const modal = document.getElementById('list-modal');
            const select = document.getElementById('filter-group');
            
            if (select.options.length === 1) {
                const groups = [...new Set(questions.map(q => q.group))];
                groups.forEach(g => {
                    const opt = document.createElement('option');
                    opt.value = g;
                    opt.textContent = g.split('·')[1] || g;
                    select.appendChild(opt);
                });
            }
            
            modal.style.display = 'flex';
            renderModalList();
        }

        function renderModalList() {
            const list = document.getElementById('modal-list');
            list.innerHTML = '';
            
            const filterGroup = document.getElementById('filter-group').value;
            const filterNum = document.getElementById('filter-num').value.trim();
            
            displayOrder.forEach((qIdx, i) => {
                const q = questions[qIdx];
                
                if (filterGroup !== 'all' && q.group !== filterGroup) return;
                if (filterNum && q.originalNum !== filterNum) return;
                
                const div = document.createElement('div');
                div.className = `modal-item ${learnedSet.has(q.id) ? 'learned' : ''}`;
                div.innerHTML = `<b>第 ${q.originalNum} 題</b> <span style="font-size:0.85rem;color:#94a3b8;">(${q.group.split('·')[1].trim()})</span><br>${q.title.replace(/<[^>]*>/g, '').substring(0, 25)}...`;
                div.onclick = () => {
                    currentIndex = i;
                    render();
                    closeModal(null, 'list-modal');
                };
                list.appendChild(div);
            });
        }

        function showSettingsModal() {
            document.getElementById('chk-opt').checked = config.shuffleOpts;
            document.getElementById('chk-qs').checked = config.shuffleQs;
            document.getElementById('settings-modal').style.display = 'flex';
        }

        function closeModal(e, modalId) {
            if(e) e.stopPropagation();
            document.getElementById(modalId).style.display = 'none';
        }

        window.onkeydown = (e) => {
            const listModal = document.getElementById('list-modal');
            const settingsModal = document.getElementById('settings-modal');
            
            if (listModal.style.display === 'flex' || settingsModal.style.display === 'flex') {
                if (e.key === 'Escape') {
                    listModal.style.display = 'none';
                    settingsModal.style.display = 'none';
                }
                return;
            }

            const app = document.getElementById('app');
            if (e.key === 'Enter') markLearned();
            if (e.key === 'ArrowRight') next();
            if (e.key === 'ArrowLeft') prev();
            if (e.key === ' ') { e.preventDefault(); toggleControls(); }
            if (['1','2','3','4'].includes(e.key)) checkAnswer(parseInt(e.key)-1);
            if (e.key === 'ArrowUp') { e.preventDefault(); app.scrollBy(0, -100); }
            if (e.key === 'ArrowDown') { e.preventDefault(); app.scrollBy(0, 100); }
        };

        initQuestions();
        syncOrder();
        render();
    </script>
</body>
</html>
"""
    output_path = os.path.join(desktop, "index.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content.replace("__DATA__", json.dumps(all_questions, ensure_ascii=False)))
    
    print("-" * 51)
    print(f"✅ Build Finished! Total: {len(all_questions)} items.")
    print(f"💾 Saved to: {output_path} (已更名為 index.html 供 GitHub Pages 使用)")
    print("-" * 51)

if __name__ == "__main__":
    main()