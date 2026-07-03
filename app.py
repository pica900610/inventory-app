import streamlit as st
import pandas as pd
import os
from datetime import datetime
import pytz  

# 設定網頁標題與圖示
st.set_page_config(page_title="簡易進銷存管理系統", page_icon="📦", layout="centered")

DB_FILE = "web_inventory_db.csv"
LOG_FILE = "web_inventory_log.csv"

# --- 資料庫初始化 ---
if not os.path.exists(DB_FILE):
    df = pd.DataFrame(columns=["商品編號", "商品名稱", "目前庫存", "安全庫存"])
    df.to_csv(DB_FILE, index=False, encoding="utf-8-sig")

if not os.path.exists(LOG_FILE):
    df_log = pd.DataFrame(columns=["時間", "商品編號", "商品名稱", "動作", "數量"])
    df_log.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")

# 讀取資料
df_stock = pd.read_csv(DB_FILE, encoding="utf-8-sig", dtype={"商品編號": str})
df_log = pd.read_csv(LOG_FILE, encoding="utf-8-sig", dtype={"商品編號": str})

# --- 初始化頁面狀態 (Session State) ---
if "current_page" not in st.session_state:
    st.session_state.current_page = "📊 庫存報表"

# --- 功能列：直接列出按鈕 ---
st.sidebar.markdown("### 🛠️ 功能選單")

# 定義所有功能
menu_items = ["📊 庫存報表", "➕ 新增商品", "📥 商品進貨", "📤 商品出貨", "📜 進出貨流水帳"]

# 用迴圈直接列出按鈕，點擊後自動記錄頁面並強制收回側邊欄
for item in menu_items:
    # 如果是目前選中的頁面，按鈕加個【型態】做視覺區隔
    type_style = "primary" if st.session_state.current_page == item else "secondary"
    
    if st.sidebar.button(item, use_container_width=True, type=type_style):
        st.session_state.current_page = item
        # 關鍵：利用 streamlit 的內建機制，當按下按鈕觸發頁面重新渲染時，手機版側邊欄會自動收回

# 取得目前點選的頁面
choice = st.session_state.current_page

# --- 網頁主要內容 ---
st.title("📦 簡易網頁版進銷存系統")

# --- 功能 1：庫存報表 ---
if choice == "📊 庫存報表":
    st.subheader("當前庫存狀態")
    
    if df_stock.empty:
        st.info("📭 目前倉庫空空如也，請先點選左側「➕ 新增商品」喔！")
    else:
        def check_status(row):
            return "⚠️ 補貨警告" if row["目前庫存"] <= row["安全庫存"] else "正常"
        
        df_display = df_stock.copy()
        df_display["狀態"] = df_display.apply(check_status, axis=1)
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        low_stock = df_display[df_display["狀態"] == "⚠️ 補貨警告"]
        if not low_stock.empty:
            st.warning(f"注意！目前有 {len(low_stock)} 項商品低於安全庫存，請儘速補貨！")

# --- 功能 2：新增商品 ---
elif choice == "➕ 新增商品":
    st.subheader("建立新商品品項")
    
    with st.form("add_product_form", clear_on_submit=True):
        p_id = st.text_input("商品編號 (例如：A001)*").strip()
        p_name = st.text_input("商品名稱 (例如：好喝紅茶)*").strip()
        p_init = st.number_input("初始庫存量", min_value=0, value=0, step=1)
        p_safe = st.number_input("安全庫存量 (低於此數量會發出警告)", min_value=0, value=5, step=1)
        
        submit = st.form_submit_button("確認建立商品")
        
        if submit:
            if not p_id or not p_name:
                st.error("❌ 商品編號與名稱為必填欄位！")
            elif p_id in df_stock["商品編號"].values:
                st.error(f"❌ 商品編號【{p_id}】已經存在了！")
            else:
                new_row = pd.DataFrame([{"商品編號": p_id, "商品名稱": p_name, "目前庫存": p_init, "安全庫存": p_safe}])
                df_stock = pd.concat([df_stock, new_row], ignore_index=True)
                df_stock.to_csv(DB_FILE, index=False, encoding="utf-8-sig")

                import pytz  # 記得在檔案最上方 import 喔！

                # 強制使用台北時間 (UTC+8)
                tw_tz = pytz.timezone("Asia/Taipei")
                now = datetime.now(tw_tz).strftime("%Y-%m-%d %H:%M:%S")
                new_log = pd.DataFrame([{"時間": now, "商品編號": p_id, "商品名稱": p_name, "動作": "初始建立", "數量": p_init}])
                df_log = pd.concat([df_log, new_log], ignore_index=True)
                df_log.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
                
                st.success(f"✅ 商品【{p_name}】成功建立！")

# --- 功能 3：商品進貨 ---
elif choice == "📥 商品進貨":
    st.subheader("商品進貨入庫")
    
    if df_stock.empty:
        st.info("📭 目前沒有商品，請先去新增商品。")
    else:
        prod_options = [f"{row['商品編號']} - {row['商品名稱']}" for _, row in df_stock.iterrows()]
        selected_prod = st.selectbox("請選擇進貨商品", prod_options)
        
        p_id = selected_prod.split(" - ")[0]
        p_name = selected_prod.split(" - ")[1]
        
        qty = st.number_input("進貨數量", min_value=1, value=1, step=1)
        
        if st.button("確認進貨", type="primary"):
            idx = df_stock[df_stock["商品編號"] == p_id].index[0]
            df_stock.at[idx, "目前庫存"] += qty
            df_stock.to_csv(DB_FILE, index=False, encoding="utf-8-sig")

            # 強制使用台北時間 (UTC+8)
            tw_tz = pytz.timezone("Asia/Taipei")
            now = datetime.now(tw_tz).strftime("%Y-%m-%d %H:%M:%S")
            new_log = pd.DataFrame([{"時間": now, "商品編號": p_id, "商品名稱": p_name, "動作": "進貨", "數量": qty}])
            df_log = pd.concat([df_log, new_log], ignore_index=True)
            df_log.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
            
            st.success(f"🎉 進貨成功！【{p_name}】目前庫存：{df_stock.at[idx, '目前庫存']}")

# --- 功能 4：商品出貨 ---
elif choice == "📤 商品出貨":
    st.subheader("商品出貨扣庫存")
    
    if df_stock.empty:
        st.info("📭 目前沒有商品，請先去新增商品。")
    else:
        prod_options = [f"{row['商品編號']} - {row['商品名稱']} (剩餘: {row['目前庫存']})" for _, row in df_stock.iterrows()]
        selected_prod = st.selectbox("請選擇出貨商品", prod_options)
        
        p_id = selected_prod.split(" - ")[0]
        p_name = selected_prod.split(" - ")[1].split(" (")[0]
        
        idx = df_stock[df_stock["商品編號"] == p_id].index[0]
        current_qty = df_stock.at[idx, "目前庫存"]
        
        qty = st.number_input("出貨數量", min_value=1, max_value=int(current_qty) if current_qty > 0 else 1, value=1, step=1)
        
        if st.button("確認出貨", type="primary"):
            if current_qty <= 0:
                st.error("❌ 該商品目前沒有庫存，無法出貨！")
            elif qty > current_qty:
                st.error(f"❌ 庫存不足！目前僅剩 {current_qty} 件。")
            else:
                df_stock.at[idx, "目前庫存"] -= qty
                df_stock.to_csv(DB_FILE, index=False, encoding="utf-8-sig")
                
               # 強制使用台北時間 (UTC+8)
                tw_tz = pytz.timezone("Asia/Taipei")
                now = datetime.now(tw_tz).strftime("%Y-%m-%d %H:%M:%S")
                new_log = pd.DataFrame([{"時間": now, "商品編號": p_id, "商品名稱": p_name, "動作": "出貨", "數量": qty}])
                df_log = pd.concat([df_log, new_log], ignore_index=True)
                df_log.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
                
                st.success(f"🚀 出貨成功！【{p_name}】剩餘庫存：{df_stock.at[idx, '目前庫存']}")
                
                if df_stock.at[idx, "目前庫存"] <= df_stock.at[idx, "安全庫存"]:
                    st.warning(f"⚠️ 警報：該商品數量已低於安全庫存量 ({df_stock.at[idx, '安全庫存']})！")

# --- 功能 5：歷史日誌 ---
elif choice == "📜 進出貨流水帳":
    st.subheader("進出貨歷史紀錄")
    if df_log.empty:
        st.info("📜 目前尚無任何進出貨紀錄。")
    else:
        st.dataframe(df_log.iloc[::-1], use_container_width=True, hide_index=True)
