import requests
import json
import os
import datetime
from datetime import timedelta, timezone

# ================= ⚙️ 配置区 =================
# 1. 核心数据源 (BestInSlot V2 - 速度最快)
HOLDERS_URL = "https://v2api.bestinslot.xyz/brc2.0/holders?tick=acorns"

# 2. 辅助数据源 (BRC20 Build - 用于查历史)
EXPLORER_API = "https://explorer.brc20.build/api/v2"
TOKEN_CONTRACT = "0x4aa8e9ca6d90e2e47b44336aa4725894332c1b16"
PROJECT_WALLET = "0xa07764097a4da7f3b61a562ca1f8e6779494748c"

# BIS SWAP 和 BIS AMM 目标地址
BIS_SWAP_ADDRESS = "0x62879BB3dD949c4CF06f71BF7c281DcF24D163e7"
BIS_AMM_ADDRESS = "0x17DBb1fA0c7A70dB033E91d080ed0b87bc6Bd542"

# 3. 代币总量 (用于计算占比)
TOTAL_SUPPLY = 999703067

# 4. 文件名 (保持您当前的设置)
DB_FILE = "acorns_light_db.json"
HTML_FILE = "acorns_monitor_v35_plus.html"

# 5. 备注名单
WATCHLIST = {
    "0xa07764097a4da7f3b61a562ca1f8e6779494748c": "🥇 榜一 (项目方)",
    "0x899cdf7bf5cf1c5a1b3c9afab2faf55482b97662": "🥈 榜二 (池子)",
        "0xbacb6e7774bb84dfcc0f5ad89c51782eade91f7e": "大宇钱包",
    "0xd3a5b717ab78f6075def527f070b9ee0dc662828": "BIS",
    "0x63160c1f9f071b57b6860bd8de66c7cb87295014": "CATSWAP",
    "0xf97ed5736eb42b0056b030e56349b3f48fce1898": "岩姐线上伙伴--8sats",
    "0xb7f1b7b18c070f998320ca75d1f1e1e33d7ab421": "岩姐团队长吕小金&J K--8.5sats",
    "0xb9d545610680be42046a75d51b199b107cb51c6c": "岩姐伙伴陈老师9.3sats",
    "0x4508cd33faa924f0104071a9c20d8f558d3d3598": "卢总钱包地址1",
    "0x5f0e77e6acef04eae1aab71f28ef71159fcb2f12": "卢总钱包地址2",
    "0x440264da99dd5502d815124951c3e03affe7a284": "温州张余寿",
    "0x757e9b4bd0f30807510e96058a64d65006c5aef5": "王金龙地址",
    "0x56153c064c9fee25bc79ad8ca6bfac7212ab4c5c": "疑似项目方",
    "0xa6ce3189f420f0fd9e90760ad1e80ce1489e3b5e": "项目方相关1",
    "0x1f40dd141d78ad7abb84b92a1bc112b0332f1ca9": "项目方相关2",
    "0x971a72167acb3e0dfa6bb5092ad3361d02a1ba5a": "项目方相关3",
    "0x3263b632d5316a187f919d58750df082ebac9568": "项目方相关4",
    "0x6f69b0f14c37c90e7cce8c019a09ad8e1f2f66a9": "项目方相关5",
    "0xf470ccb11c23250ebae4bc632ffe93961850a63e": "王金龙线上营销",
    "0xa648ab10aa4b6911e80b58fef5f402bed96a93bc": "王金龙地址2",
    "0x7eac9d9f054d12aa6e2d499e181f5932ddc41a8c": "王金龙地址3",
    "0x4ba15fd51f5ab0c31233893df6cd08283b580a0a": "王金龙地址4",
    "0x881a670564867d6af6f8b9a47b9b14186d4523b3": "王金龙地址5",
    "0xe513a6fb5fed9fe4d5abbc7f1fe64cec568fba18": "王金龙地址6",
    "0x758f29be1e23ba21a5b69c1024db4e4b33e9fc50": "王金龙地址7",
    "0x02e4b4cb9c796fa67b27b40e7a004a9180a4e4e0": "王金龙地址8",
    "0x170e7baf244a95989d059b5a4af7a27a4e712616": "105nft",
    "0xa1763467317d8f18955c06e8be2d1909c6b611e2": "105nft",
    "0xd00a593da9d9f5769b4bcbb657d3559960165299": "101nft",
    "0x8893002cf5978378db25f4648ab295ee0b0e54c5": "卢总钱包地址3"
}
# ============================================

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: return {}
    return {}

# === 核心功能 1: 深度溯源 MINT 名单 ===
def fetch_mint_list_deep():
    print(f"🕵️‍♂️ [1/3] 正在全量扫描项目方历史，寻找 MINT 地址...")
    print("⏳ 正在翻阅链上账本 (为了不漏掉早期地址，这需要一点时间)...")

    minters = set()
    url = f"{EXPLORER_API}/addresses/{PROJECT_WALLET}/token-transfers"
    params = {"token": TOKEN_CONTRACT, "type": "ERC-20", "limit": 50}
    headers = {"User-Agent": "Mozilla/5.0"}

    total_scanned = 0

    while True:
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code != 200: break

            data = resp.json()
            items = data.get('items', [])
            if not items: break

            total_scanned += len(items)
            print(f"   已扫描 {total_scanned} 笔交易...", end="\r")

            for item in items:
                # 校验合约
                if item.get('token', {}).get('address', '').lower() != TOKEN_CONTRACT.lower(): continue

                from_addr = item.get('from', {}).get('hash', '').lower()
                to_addr = item.get('to', {}).get('hash', '').lower()

                # 项目方发出去的 -> 接收者就是 Minter
                if from_addr == PROJECT_WALLET.lower():
                    minters.add(to_addr)

            # 翻页逻辑
            if 'next_page_params' in data and data['next_page_params']:
                params.update(data['next_page_params'])
            else:
                break
        except: break

    print(f"\n✅ MINT 名单建立完毕！共发现 {len(minters)} 个原始地址。")
    return minters

# === 核心功能 2: 智能验真 ===
def check_is_truly_new(address):
    url = f"{EXPLORER_API}/addresses/{address}/token-transfers"
    params = {"token": TOKEN_CONTRACT, "type": "ERC-20", "limit": 10}
    try:
        resp = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if resp.status_code == 200:
            items = resp.json().get('items', [])
            if not items: return True # 无记录，肯定是新人

            # 检查是否有早于24小时的交易
            now = datetime.datetime.now(timezone.utc)
            for item in items:
                ts_str = item.get('timestamp')
                try:
                    dt = datetime.datetime.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                    if (now - dt).total_seconds() > 86400: return False # 是老手回归
                except: pass
    except: pass
    return True

# === 核心功能 3: 获取目标地址的所有转账记录 ===
def get_transfers(target_address, direction="incoming"):
    """
    获取目标地址的转账记录
    参数：
        target_address: 目标地址（如 bis swap 或 bis amm）
        direction: "incoming" 接收记录, "outgoing" 发送记录
    返回：
        字典：{地址: 总数量}
    """
    url = f"{EXPLORER_API}/addresses/{target_address}/token-transfers"
    params = {"token": TOKEN_CONTRACT, "type": "ERC-20", "limit": 100}
    headers = {"User-Agent": "Mozilla/5.0"}

    transfer_data = {}  # {address: total_amount}

    print(f"   📡 正在查询 {direction}: {url}")
    print(f"   🔑 目标地址: {target_address}")

    try:
        page_count = 0
        while True:
            page_count += 1
            resp = requests.get(url, params=params, headers=headers, timeout=10)

            if resp.status_code != 200:
                print(f"   ⚠️ 请求失败 (第{page_count}页): 状态码 {resp.status_code}")
                break

            data = resp.json()
            items = data.get('items', [])

            if not items:
                print(f"   📄 第{page_count}页: 没有更多数据")
                break

            print(f"   📄 第{page_count}页: 获取到 {len(items)} 条记录")

            # 调试: 显示前3条记录
            if page_count == 1:
                print(f"   🔍 前3条记录示例:")
                for i, item in enumerate(items[:3]):
                    from_addr = item.get('from', {}).get('hash', '')
                    to_addr = item.get('to', {}).get('hash', '')
                    token_addr = item.get('token', {}).get('address', '')
                    amount = float(item.get('value', 0) or 0)
                    decimals = int(item.get('token', {}).get('decimals', 18))
                    actual_amount = amount / (10 ** decimals)
                    print(f"      {i+1}. 发送方: {from_addr[:20]}... → 接收方: {to_addr[:20]}... | 金额: {actual_amount:.2f} | 合约: {token_addr[:20]}...")

            for item in items:
                # 校验合约
                token_addr = item.get('token', {}).get('address', '')
                if token_addr.lower() != TOKEN_CONTRACT.lower():
                    continue

                # 获取发送方和接收方地址
                from_addr = item.get('from', {}).get('hash', '').lower()
                to_addr = item.get('to', {}).get('hash', '').lower()

                # 忽略零地址和空地址
                if not from_addr or from_addr == '0x0000000000000000000000000000000000000000':
                    continue

                # 计算金额 - API 返回的 value 在 total 对象下
                total_data = item.get('total', {})
                amount = float(total_data.get('value', 0) or 0)
                decimals = int(total_data.get('decimals', 18))
                actual_amount = amount / (10 ** decimals)

                # 根据方向统计
                if direction == "incoming":
                    # 统计发送到目标地址的记录
                    if to_addr == target_address.lower():
                        counterparty = from_addr
                    else:
                        continue
                else:  # outgoing
                    # 统计从目标地址发送出去的记录
                    if from_addr == target_address.lower():
                        counterparty = to_addr
                    else:
                        continue

                # 累加到字典
                if counterparty not in transfer_data:
                    transfer_data[counterparty] = 0.0
                transfer_data[counterparty] += actual_amount

            # 翻页逻辑
            if 'next_page_params' in data and data['next_page_params']:
                params.update(data['next_page_params'])
            else:
                break

        # 统计总金额
        total_amount = sum(transfer_data.values())
        direction_name = "接收" if direction == "incoming" else "发送"
        print(f"   ✅ {target_address}: 找到 {len(transfer_data)} 个{direction_name}地址, 总计 {total_amount:.2f} 代币")

        # 显示前5个最大的
        if transfer_data:
            sorted_parties = sorted(transfer_data.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"   📊 前5大{direction_name}方:")
            for addr, amount in sorted_parties:
                print(f"      {addr[:20]}... → {amount:.2f} 代币")

    except Exception as e:
        print(f"   ⚠️ 获取 {target_address} {direction}记录失败: {e}")
        import traceback
        traceback.print_exc()

    return transfer_data

# === 保存 BIS 数据到文件 ===
def save_bis_data(bis_swap_data, bis_amm_data, lp_data=None):
    """将 BIS SWAP 和 BIS AMM 的数据保存到文件，方便调试"""
    bis_data = {
        "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
        "bis_swap": {
            "address": BIS_SWAP_ADDRESS,
            "incoming": {
                "total_senders": len(bis_swap_data.get("incoming", {})),
                "total_amount": sum(bis_swap_data.get("incoming", {}).values()),
                "top_senders": [
                    {"address": addr, "amount": amount}
                    for addr, amount in sorted(bis_swap_data.get("incoming", {}).items(), key=lambda x: x[1], reverse=True)[:20]
                ]
            },
            "outgoing": {
                "total_receivers": len(bis_swap_data.get("outgoing", {})),
                "total_amount": sum(bis_swap_data.get("outgoing", {}).values()),
                "top_receivers": [
                    {"address": addr, "amount": amount}
                    for addr, amount in sorted(bis_swap_data.get("outgoing", {}).items(), key=lambda x: x[1], reverse=True)[:20]
                ]
            }
        },
        "bis_amm": {
            "address": BIS_AMM_ADDRESS,
            "incoming": {
                "total_senders": len(bis_amm_data.get("incoming", {})),
                "total_amount": sum(bis_amm_data.get("incoming", {}).values()),
                "top_senders": [
                    {"address": addr, "amount": amount}
                    for addr, amount in sorted(bis_amm_data.get("incoming", {}).items(), key=lambda x: x[1], reverse=True)[:20]
                ]
            },
            "outgoing": {
                "total_receivers": len(bis_amm_data.get("outgoing", {})),
                "total_amount": sum(bis_amm_data.get("outgoing", {}).values()),
                "top_receivers": [
                    {"address": addr, "amount": amount}
                    for addr, amount in sorted(bis_amm_data.get("outgoing", {}).items(), key=lambda x: x[1], reverse=True)[:20]
                ]
            }
        }
    }

    # 添加流动性提供者数据
    if lp_data:
        bis_data["liquidity_providers"] = {
            "total_count": lp_data.get("total_lp_count", 0),
            "top_providers": [
                {
                    "address": addr,
                    "net_inflow": data['net'],
                    "total_in": data['in'],
                    "total_out": data['out']
                }
                for addr, data in list(lp_data.get("lp_providers", {}).items())[:20]
            ]
        }

    with open('bis_data_debug.json', 'w', encoding='utf-8') as f:
        json.dump(bis_data, f, indent=2, ensure_ascii=False)

    print(f"   💾 BIS 数据已保存到 bis_data_debug.json")
    print(f"   📊 BIS SWAP: 转入 {len(bis_swap_data.get('incoming', {}))} 个, 转出 {len(bis_swap_data.get('outgoing', {}))} 个")
    print(f"   📊 BIS AMM: 转入 {len(bis_amm_data.get('incoming', {}))} 个, 转出 {len(bis_amm_data.get('outgoing', {}))} 个")

# === 主数据抓取 ===
def fetch_data(minters_set, db_old_keys):
    print(f"🚀 [2/3] 正在下载全量持仓榜...")

    # 1. 先获取 BIS SWAP 和 BIS AMM 的所有接收和发送记录
    print(f"📊 正在获取 BIS SWAP 和 BIS AMM 转账记录...")

    # BIS SWAP: 接收记录(用户 deposit)和发送记录(用户 withdraw)
    bis_swap_incoming = get_transfers(BIS_SWAP_ADDRESS, "incoming")  # +
    bis_swap_outgoing = get_transfers(BIS_SWAP_ADDRESS, "outgoing")  # -

    # BIS AMM: 接收记录(添加流动性)和发送记录(移除流动性)
    bis_amm_incoming = get_transfers(BIS_AMM_ADDRESS, "incoming")   # +
    bis_amm_outgoing = get_transfers(BIS_AMM_ADDRESS, "outgoing")    # -

    # 创建流动性提供者完整榜单（包括没有持仓的地址）
    lp_providers = {}
    for addr, amount_in in bis_amm_incoming.items():
        amount_out = bis_amm_outgoing.get(addr, 0)
        lp_providers[addr] = {
            'in': amount_in,
            'out': amount_out,
            'net': amount_in - amount_out
        }

    # 按净流入排序
    sorted_lp = sorted(lp_providers.items(), key=lambda x: x[1]['net'], reverse=True)
    print(f"\n   💎 流动性提供者统计: 找到 {len(lp_providers)} 个 LP 地址")
    print(f"   📊 前10大流动性提供者:")
    for i, (addr, data) in enumerate(sorted_lp[:10], 1):
        print(f"      {i:2d}. {addr[:20]}... → 净流入: {data['net']:,.2f} (流入: {data['in']:,.2f}, 流出: {data['out']:,.2f})")

    # 保存 BIS 数据到文件（用于调试）
    save_bis_data({
        "incoming": bis_swap_incoming,
        "outgoing": bis_swap_outgoing
    }, {
        "incoming": bis_amm_incoming,
        "outgoing": bis_amm_outgoing
    }, {
        "lp_providers": dict(sorted_lp),
        "total_lp_count": len(lp_providers)
    })

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(HOLDERS_URL, headers=headers, timeout=30)
        if resp.status_code != 200: return []
        items = resp.json().get('items', [])

        holders = []
        candidates_for_check = []

        for item in items:
            ox = item.get('evm_wallet')
            btc = item.get('btc_wallet')
            bal = float(item.get('total_balance') or item.get('evm_withdrawable_balance') or 0)

            if ox:
                key = ox.lower()
                if not btc: btc = "-"

                # 1. 判断 Mint
                is_mint = (key in minters_set)

                # 2. 计算占比
                percent = (bal / TOTAL_SUPPLY) * 100

                # 3. 获取 BIS 转账数据
                bis_swap_in = bis_swap_incoming.get(key, 0)
                bis_swap_out = bis_swap_outgoing.get(key, 0)
                bis_amm_in = bis_amm_incoming.get(key, 0)
                bis_amm_out = bis_amm_outgoing.get(key, 0)

                # 4. 计算总和：持仓 + BIS SWAP(净流入) + BIS AMM(净流入)
                # 净流入 = 转入 - 转出
                bis_swap_net = bis_swap_in - bis_swap_out
                bis_amm_net = bis_amm_in - bis_amm_out
                total_balance = bal + bis_swap_net + bis_amm_net

                # 5. 判断用户类型
                is_potential_new = (key not in db_old_keys) and (len(db_old_keys) > 0)

                # 判断是否是流动性提供者（参与了BIS AMM）
                is_lp = (bis_amm_in > 0 or bis_amm_out > 0)

                # 判断是否是交易者（只在BIS SWAP交易）
                is_trader = (bis_swap_in > 0 or bis_swap_out > 0) and not is_lp

                status = ""
                if is_lp:
                    status = "LP"  # 流动性提供者
                if is_trader:
                    status = "TRADER"  # 交易者
                if is_potential_new and not status:
                    status = "CHECKING"
                    candidates_for_check.append(key)

                holders.append({
                    "rank": len(holders) + 1,
                    "key": key,
                    "btc": btc,
                    "bal": bal,
                    "pct": percent,
                    "is_mint": is_mint,
                    "status": status,
                    "bis_swap_in": bis_swap_in,
                    "bis_swap_out": bis_swap_out,
                    "bis_amm_in": bis_amm_in,
                    "bis_amm_out": bis_amm_out,
                    "total_balance": total_balance  # 新增：总和
                })

        # === 批量验真 ===
        if candidates_for_check:
            print(f"🕵️‍♂️ [3/3] 正在核实 {len(candidates_for_check)} 个新出现的地址...")
            skip_check = len(candidates_for_check) > 50

            count = 0
            cache = {}
            for addr in candidates_for_check:
                count += 1
                if skip_check:
                    res = "NEW"
                else:
                    print(f"   核查中 ({count}/{len(candidates_for_check)})...", end="\r")
                    is_true = check_is_truly_new(addr)
                    res = "NEW" if is_true else "RETURN"

                cache[addr] = res

            for h in holders:
                if h['status'] == "CHECKING":
                    h['status'] = cache.get(h['key'], "NEW")
            print("\n✅ 核实完成。")

        return holders
    except Exception as e:
        print(f"❌ 错误: {e}")
        return []

def analyze_health_metrics(holders, db, minters_set):
    """
    分析项目健康度指标
    返回包含所有分析结果的字典
    """
    tz_cn = timezone(timedelta(hours=8))
    today_str = datetime.datetime.now(tz_cn).strftime("%Y-%m-%d")

    # === 1. 持仓集中度分析 ===
    print(f"\n📊 [健康度分析] 正在计算持仓集中度...")

    # 按持仓排序
    sorted_holders = sorted(holders, key=lambda x: x['total_balance'], reverse=True)

    # 计算前10/100/1000地址的持仓占比
    total_supply = TOTAL_SUPPLY
    top10_balance = sum(h['total_balance'] for h in sorted_holders[:10])
    top100_balance = sum(h['total_balance'] for h in sorted_holders[:100])
    top1000_balance = sum(h['total_balance'] for h in sorted_holders[:1000])

    top10_ratio = (top10_balance / total_supply * 100) if total_supply > 0 else 0
    top100_ratio = (top100_balance / total_supply * 100) if total_supply > 0 else 0
    top1000_ratio = (top1000_balance / total_supply * 100) if total_supply > 0 else 0

    # Gini系数（财富不平等指数）
    balances = [h['total_balance'] for h in holders if h['total_balance'] > 0]
    n = len(balances)
    gini = 0
    if n > 0:
        sorted_balances = sorted(balances)
        cum_income = [0]
        for b in sorted_balances:
            cum_income.append(cum_income[-1] + b)
        gini = 1 - (2 / (n * sum(sorted_balances))) * sum((n + 1 - (i + 1)) * b for i, b in enumerate(sorted_balances))

    print(f"   ✅ 前10地址占比: {top10_ratio:.2f}%")
    print(f"   ✅ 前100地址占比: {top100_ratio:.2f}%")
    print(f"   ✅ Gini系数: {gini:.3f} (0=完全平等, 1=完全不平等)")

    # === 2. 新增地址趋势 ===
    print(f"\n📈 [健康度分析] 正在分析新增地址趋势...")

    # 统计过去7天、30天的新增地址
    seven_days_ago = (datetime.datetime.now(tz_cn) - timedelta(days=7)).strftime("%Y-%m-%d")
    thirty_days_ago = (datetime.datetime.now(tz_cn) - timedelta(days=30)).strftime("%Y-%m-%d")

    new_addresses_7d = 0
    new_addresses_30d = 0
    active_addresses = 0  # 有余额变动的地址

    for key, history in db.items():
        if history:
            first_date = history[0]['t']
            if first_date >= thirty_days_ago:
                new_addresses_30d += 1
                if first_date >= seven_days_ago:
                    new_addresses_7d += 1

            # 检查是否活跃（最近7天有余额变动）
            recent_history = [h for h in history if h['t'] >= seven_days_ago]
            if len(recent_history) >= 2:
                active_addresses += 1

    total_addresses = len(db.keys())
    active_ratio = (active_addresses / total_addresses * 100) if total_addresses > 0 else 0

    print(f"   ✅ 总地址数: {total_addresses}")
    print(f"   ✅ 7日新增: {new_addresses_7d}")
    print(f"   ✅ 30日新增: {new_addresses_30d}")
    print(f"   ✅ 活跃地址: {active_addresses} ({active_ratio:.2f}%)")

    # === 3. Mint地址留存率 ===
    print(f"\n💎 [健康度分析] 正在分析Mint地址留存率...")

    mint_holders = 0
    for addr in minters_set:
        if addr in db and db[addr]:
            current_balance = db[addr][-1]['y']
            if current_balance > 0:
                mint_holders += 1

    total_minters = len(minters_set)
    mint_retention = (mint_holders / total_minters * 100) if total_minters > 0 else 0

    print(f"   ✅ Mint地址总数: {total_minters}")
    print(f"   ✅ 当前仍持有: {mint_holders}")
    print(f"   ✅ 留存率: {mint_retention:.2f}%")

    # === 4. 健康度评分 ===
    print(f"\n🏥 [健康度分析] 正在计算综合健康度评分...")

    score = 100
    score_details = []

    # 集中度评分 (30分)
    if top10_ratio <= 30:
        concentration_score = 30
        score_details.append("✅ 集中度: 优秀 (前10<30%)")
    elif top10_ratio <= 50:
        concentration_score = 20
        score_details.append("⚠️ 集中度: 良好 (前10<50%)")
    elif top10_ratio <= 70:
        concentration_score = 10
        score_details.append("⚠️ 集中度: 较高 (前10<70%)")
    else:
        concentration_score = 0
        score_details.append("❌ 集中度: 危险 (前10>70%)")
    score += concentration_score - 30

    # 活跃度评分 (25分)
    if active_ratio >= 30:
        activity_score = 25
        score_details.append("✅ 活跃度: 优秀 (>30%)")
    elif active_ratio >= 20:
        activity_score = 15
        score_details.append("⚠️ 活跃度: 良好 (>20%)")
    elif active_ratio >= 10:
        activity_score = 5
        score_details.append("⚠️ 活跃度: 一般 (>10%)")
    else:
        activity_score = 0
        score_details.append("❌ 活跃度: 较低 (<10%)")
    score += activity_score - 25

    # Mint留存率评分 (25分)
    if mint_retention >= 50:
        retention_score = 25
        score_details.append("✅ Mint留存: 优秀 (>50%)")
    elif mint_retention >= 30:
        retention_score = 15
        score_details.append("⚠️ Mint留存: 良好 (>30%)")
    elif mint_retention >= 10:
        retention_score = 5
        score_details.append("⚠️ Mint留存: 一般 (>10%)")
    else:
        retention_score = 0
        score_details.append("❌ Mint留存: 较低 (<10%)")
    score += retention_score - 25

    # 增长趋势评分 (20分)
    if new_addresses_7d >= 10:
        growth_score = 20
        score_details.append("✅ 增长趋势: 优秀 (7日新增>10)")
    elif new_addresses_7d >= 5:
        growth_score = 10
        score_details.append("⚠️ 增长趋势: 良好 (7日新增>5)")
    elif new_addresses_7d >= 1:
        growth_score = 5
        score_details.append("⚠️ 增长趋势: 缓慢 (7日新增>1)")
    else:
        growth_score = 0
        score_details.append("❌ 增长趋势: 停滞 (7日新增=0)")
    score += growth_score - 20

    # 确保分数在0-100之间
    score = max(0, min(100, score))

    # 评级
    if score >= 80:
        grade = "A"
        grade_desc = "优秀"
        color = "🟢"
    elif score >= 60:
        grade = "B"
        grade_desc = "良好"
        color = "🟡"
    elif score >= 40:
        grade = "C"
        grade_desc = "一般"
        color = "🟠"
    else:
        grade = "D"
        grade_desc = "较差"
        color = "🔴"

    print(f"\n{'='*60}")
    print(f"🎯 综合健康度评分: {score}/100 {color} [{grade}级 - {grade_desc}]")
    for detail in score_details:
        print(f"   {detail}")
    print(f"{'='*60}\n")

    # 返回所有分析结果
    return {
        "timestamp": datetime.datetime.now(tz_cn).isoformat(),
        "date": today_str,
        "score": score,
        "grade": grade,
        "grade_desc": grade_desc,
        "score_details": score_details,
        "metrics": {
            "concentration": {
                "top10_ratio": round(top10_ratio, 2),
                "top100_ratio": round(top100_ratio, 2),
                "top1000_ratio": round(top1000_ratio, 2),
                "gini": round(gini, 3)
            },
            "activity": {
                "total_addresses": total_addresses,
                "active_addresses": active_addresses,
                "active_ratio": round(active_ratio, 2),
                "new_addresses_7d": new_addresses_7d,
                "new_addresses_30d": new_addresses_30d
            },
            "mint_retention": {
                "total_minters": total_minters,
                "mint_holders": mint_holders,
                "retention_rate": round(mint_retention, 2)
            }
        }
    }

def generate_report(holders, db, health_report=None):
    chart_data = {}

    # === 北京时间修正 (UTC+8) ===
    tz_cn = timezone(timedelta(hours=8))
    today_str = datetime.datetime.now(tz_cn).strftime("%Y-%m-%d")

    table_data = []

    # 创建当前持有人字典
    current_holders = {h['key']: h for h in holders}

    # 处理所有历史地址（包括当前余额为0的）
    all_keys = set(db.keys()) | set(current_holders.keys())

    for key in all_keys:
        # 如果是当前持有人，使用最新数据
        if key in current_holders:
            h = current_holders[key]
        else:
            # 如果不在当前持有人列表，创建一个空记录
            h = {
                'key': key,
                'btc': '-',
                'bal': 0,
                'pct': 0,
                'is_mint': False,
                'status': 'SOLD_OUT',  # 已卖完
                'bis_swap_in': 0,
                'bis_swap_out': 0,
                'bis_amm_in': 0,
                'bis_amm_out': 0,
                'total_balance': 0,
                'rank': 9999
            }

        # 如果没有历史记录，跳过（新地址但余额为0的）
        if key not in db or not db[key]:
            if h['bal'] == 0 and h['total_balance'] == 0:
                continue

        if key not in db: db[key] = []
        history = db[key]

        # 历史记录逻辑 - 使用 total_balance 而不是 bal
        if not history or history[-1]['t'] != today_str:
            if history:
                try:
                    last = datetime.datetime.strptime(history[-1]['t'], "%Y-%m-%d").date()
                    current_date_obj = datetime.datetime.strptime(today_str, "%Y-%m-%d").date()
                    delta = (current_date_obj - last).days
                    if delta > 1:
                        for i in range(1, delta):
                            d = (last + timedelta(days=i)).strftime("%Y-%m-%d")
                            history.append({"t": d, "y": history[-1]['y']})
                except: pass
            # 存储总和（持仓 + BIS SWAP净流入 + BIS AMM净流入）
            history.append({"t": today_str, "y": h['total_balance']})
        else:
            # 更新今天的值
            history[-1]['y'] = h['total_balance']

        if len(history) > 180: history = history[-180:]
        db[key] = history

        # 24H变化 - 基于总和计算
        change = 0
        if len(history) >= 2:
            raw_change = h['total_balance'] - history[-2]['y']
            if abs(raw_change) >= 1: change = raw_change

        chart_data[key] = history

        note = WATCHLIST.get(key, "")
        if h['is_mint'] and key != PROJECT_WALLET.lower():
            note = "🎁 [MINT] " + note

        # 计算BIS净流入
        bis_swap_net = h.get('bis_swap_in', 0) - h.get('bis_swap_out', 0)
        bis_amm_net = h.get('bis_amm_in', 0) - h.get('bis_amm_out', 0)

        table_data.append({
            "rank": h['rank'],
            "key": key,
            "btc": h['btc'],
            "bal": h['bal'],  # 原始持仓
            "pct": h['pct'],
            "change": change,  # 基于 total_balance 的24H变化
            "note": note,
            "status": h['status'],
            "is_new_day": (len(history) == 1),
            "bis_swap_in": h.get('bis_swap_in', 0),
            "bis_swap_out": h.get('bis_swap_out', 0),
            "bis_swap_net": bis_swap_net,  # BIS SWAP净流入，用于排序
            "bis_amm_in": h.get('bis_amm_in', 0),
            "bis_amm_out": h.get('bis_amm_out', 0),
            "bis_amm_net": bis_amm_net,  # BIS AMM净流入，用于排序
            "total_balance": h['total_balance']  # 总和
        })

    # 按总和排序，已卖完的（总和<=0）排在后面
    table_data.sort(key=lambda x: x['total_balance'], reverse=True)

    save_db(db)

    # === HTML 生成 ===
    json_chart = json.dumps(chart_data)
    json_table = json.dumps(table_data)
    json_health = json.dumps(health_report) if health_report else "null"

    # === 北京时间显示 ===
    now = datetime.datetime.now(tz_cn).strftime("%Y-%m-%d %H:%M")

    html = f"""
    <!DOCTYPE html><html><head><meta charset="utf-8"><title>ACORNS V35+ 融合版</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body{{background:#121212;color:#ccc;font-family:sans-serif;padding:20px}}
        h1{{text-align:center;color:#00bcd4}} .info{{text-align:center;color:#666}}

        .controls {{text-align:center; margin:20px 0;}}
        input {{background:#333;border:1px solid #555;color:#fff;padding:8px;border-radius:4px;width:300px}}

        table{{width:100%;border-collapse:collapse;background:#1e1e1e;font-size:13px}}
        th,td{{padding:10px;border-bottom:1px solid #333;text-align:left}}
        th{{background:#252525;color:#888;cursor:pointer;user-select:none}}
        th:hover{{color:#fff;background:#333}}

        .addr-0x{{color:#00bcd4;font-family:monospace;display:block}}
        .addr-btc{{color:#666;font-size:11px;font-family:monospace}}
        .up{{color:#f44336}} .down{{color:#4caf50}}

        .mint-tag{{background:#9c27b0;color:#fff;padding:2px 4px;font-size:10px;border-radius:3px;font-weight:bold;margin-right:4px}}
        .new-tag{{background:#f44336;color:#fff;padding:2px 4px;font-size:10px;border-radius:3px;margin-right:4px}}
        .ret-tag{{background:#2196F3;color:#fff;padding:2px 4px;font-size:10px;border-radius:3px;margin-right:4px}}
        .lp-tag{{background:#00e676;color:#000;padding:2px 4px;font-size:10px;border-radius:3px;font-weight:bold;margin-right:4px}}
        .trader-tag{{background:#ff9800;color:#000;padding:2px 4px;font-size:10px;border-radius:3px;font-weight:bold;margin-right:4px}}
        .soldout-tag{{background:#607d8b;color:#fff;padding:2px 4px;font-size:10px;border-radius:3px;margin-right:4px}}
        .rem{{background:#9e9e9e;color:#fff;padding:2px 4px;font-size:10px;border-radius:3px}}

        .btn{{background:#333;border:1px solid #555;color:#fff;cursor:pointer;padding:4px 8px;border-radius:4px}}

        /* 健康度面板样式 */
        .health-panel{{background:#1e1e1e;border:2px solid #333;border-radius:8px;padding:20px;margin:20px 0;}}
        .health-title{{font-size:18px;font-weight:bold;margin-bottom:15px;text-align:center;color:#00bcd4}}
        .health-score{{text-align:center;margin:20px 0;}}
        .score-circle{{display:inline-block;width:120px;height:120px;border-radius:50%;border:6px solid #00bcd4;text-align:center;line-height:108px;font-size:36px;font-weight:bold;}}
        .score-a{{border-color:#4caf50;color:#4caf50}}
        .score-b{{border-color:#ffeb3b;color:#ffeb3b}}
        .score-c{{border-color:#ff9800;color:#ff9800}}
        .score-d{{border-color:#f44336;color:#f44336}}
        .health-metrics{{display:grid;grid-template-columns:repeat(auto-fit, minmax(250px, 1fr));gap:15px;margin-top:20px}}
        .metric-card{{background:#252525;padding:15px;border-radius:6px;border-left:4px solid #00bcd4}}
        .metric-label{{font-size:12px;color:#888;margin-bottom:5px}}
        .metric-value{{font-size:20px;font-weight:bold;color:#fff}}
        .metric-sub{{font-size:11px;color:#666;margin-top:3px}}

        #modal{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:999}}
        .box{{background:#222;margin:5% auto;width:90%;max-width:900px;height:500px;padding:20px;border-radius:8px;position:relative}}
        .close{{position:absolute;top:10px;right:15px;font-size:24px;cursor:pointer;color:#fff}}
    </style></head><body>

    <h1>🌰 ACORNS V35+ (终极融合版)</h1>
    <div class="info">总人数: <span id="count">{len(holders)}</span> | 更新: {now} (北京时间)</div>

    <!-- 健康度面板 -->
    <div class="health-panel" id="healthPanel" style="display:none;">
        <div class="health-title">🏥 项目健康度分析</div>
        <div class="health-score">
            <div class="score-circle" id="scoreCircle">--</div>
            <div style="margin-top:10px;font-size:14px;color:#888;" id="scoreGrade">分析中...</div>
        </div>
        <div class="health-metrics" id="healthMetrics">
            <!-- 动态生成指标卡片 -->
        </div>
    </div>

    <div class="controls">
        <input type="text" id="search" placeholder="🔍 搜索地址 / LP / TRADER / MINT / NEW / 备注..." onkeyup="render()">
    </div>

    <div class="controls" style="margin-top: 15px;">
        <button class="btn" onclick="changePageSize()">📄 每页显示: <span id="pageSizeLabel">100</span></button>
        <span id="pageInfo" style="margin-left: 20px; color: #aaa;"></span>
        <button class="btn" onclick="prevPage()" style="margin-left: 10px;">⬅️ 上一页</button>
        <button class="btn" onclick="nextPage()" style="margin-left: 5px;">➡️ 下一页</button>
    </div>

    <table>
        <thead>
            <tr>
                <th onclick="sort('rank')" style="width:60px;">排名 ⇵</th>
                <th onclick="sort('key')">地址 (0x / btc)</th>
                <th onclick="sort('bal')" style="width:120px;">持仓 ⇵</th>
                <th onclick="sort('bis_swap_net')" style="width:130px;">BIS SWAP ⇵<br><span style="font-size:10px;color:#666">净流入(+/-)</span></th>
                <th onclick="sort('bis_amm_net')" style="width:130px;">BIS AMM ⇵<br><span style="font-size:10px;color:#666">净流入(+/-)</span></th>
                <th onclick="sort('total_balance')" style="width:130px;">总和 ⇵</th>
                <th onclick="sort('pct')" style="width:90px;">占比 % ⇵</th>
                <th onclick="sort('change')" style="width:130px;">24H 变化 ⇵</th>
                <th style="width:60px;">趋势</th>
            </tr>
        </thead>
        <tbody id="tbody"></tbody>
    </table>

    <div id="modal"><div class="box"><span class="close" onclick="document.getElementById('modal').style.display='none'">&times;</span><canvas id="c"></canvas></div></div>

    <script>
    let rawData = {json_table};
    const chartData = {json_chart};
    const healthData = {json_health};  // 健康度数据
    let sortCol = 'total_balance';  // 默认按总和排序
    let sortDesc = true;

    // 分页配置
    let currentPage = 1;
    let pageSize = 100;
    let filteredAndSortedData = [];  // 缓存过滤和排序后的数据

    // 显示健康度面板
    function displayHealthPanel() {{
        if (!healthData) return;

        const panel = document.getElementById('healthPanel');
        const scoreCircle = document.getElementById('scoreCircle');
        const scoreGrade = document.getElementById('scoreGrade');
        const metricsDiv = document.getElementById('healthMetrics');

        // 显示面板
        panel.style.display = 'block';

        // 设置评分圆圈
        const score = healthData.score;
        const grade = healthData.grade;
        const gradeDesc = healthData.grade_desc;

        scoreCircle.textContent = score;
        scoreCircle.className = 'score-circle score-' + grade.toLowerCase();
        scoreGrade.textContent = `${{
            'A': '🟢 优秀 - A级',
            'B': '🟡 良好 - B级',
            'C': '🟠 一般 - C级',
            'D': '🔴 较差 - D级'
        }}[grade] || `${{grade}}级 - ${{gradeDesc}}`;

        // 生成指标卡片
        const metrics = healthData.metrics;
        let metricCards = '';

        // 集中度指标
        metricCards += `
            <div class="metric-card">
                <div class="metric-label">📊 持仓集中度</div>
                <div class="metric-value">${{metrics.concentration.top10_ratio}}%</div>
                <div class="metric-sub">前10地址占比</div>
                <div class="metric-sub">前100: ${{metrics.concentration.top100_ratio}}% | Gini: ${{metrics.concentration.gini}}</div>
            </div>
        `;

        // 活跃度指标
        const activeColor = metrics.activity.active_ratio >= 30 ? '#4caf50' : metrics.activity.active_ratio >= 20 ? '#ff9800' : '#f44336';
        metricCards += `
            <div class="metric-card" style="border-left-color:${{activeColor}}">
                <div class="metric-label">👥 地址活跃度</div>
                <div class="metric-value">${{metrics.activity.active_ratio}}%</div>
                <div class="metric-sub">活跃/总地址: ${{metrics.activity.active_addresses}}/${{metrics.activity.total_addresses}}</div>
                <div class="metric-sub">7日新增: ${{metrics.activity.new_addresses_7d}} | 30日: ${{metrics.activity.new_addresses_30d}}</div>
            </div>
        `;

        // Mint留存率指标
        const retentionColor = metrics.mint_retention.retention_rate >= 50 ? '#4caf50' : metrics.mint_retention.retention_rate >= 30 ? '#ff9800' : '#f44336';
        metricCards += `
            <div class="metric-card" style="border-left-color:${{retentionColor}}">
                <div class="metric-label">💎 Mint留存率</div>
                <div class="metric-value">${{metrics.mint_retention.retention_rate}}%</div>
                <div class="metric-sub">当前持有/总Mint: ${{metrics.mint_retention.mint_holders}}/${{metrics.mint_retention.total_minters}}</div>
            </div>
        `;

        // 风险提示
        let riskLevel = '低';
        let riskColor = '#4caf50';
        if (metrics.concentration.top10_ratio > 70) {{
            riskLevel = '高';
            riskColor = '#f44336';
        }} else if (metrics.concentration.top10_ratio > 50) {{
            riskLevel = '中';
            riskColor = '#ff9800';
        }}

        metricCards += `
            <div class="metric-card" style="border-left-color:${{riskColor}}">
                <div class="metric-label">⚠️ 风险评估</div>
                <div class="metric-value" style="color:${{riskColor}}">${{riskLevel}}</div>
                <div class="metric-sub">基于集中度、活跃度综合评估</div>
            </div>
        `;

        metricsDiv.innerHTML = metricCards;
    }}

    function render() {{
        const tbody = document.getElementById('tbody');
        const search = document.getElementById('search').value.toLowerCase();

        // 过滤数据
        filteredAndSortedData = rawData.filter(item =>
            item.key.includes(search) || item.btc.includes(search) || item.note.toLowerCase().includes(search) || item.status.toLowerCase().includes(search)
        );

        document.getElementById('count').innerText = filteredAndSortedData.length;

        // 排序数据（只在排序时执行一次）
        filteredAndSortedData.sort((a, b) => {{
            let valA = a[sortCol];
            let valB = b[sortCol];
            if (typeof valA === 'string') return sortDesc ? valB.localeCompare(valA) : valA.localeCompare(valB);
            return sortDesc ? (valB - valA) : (valA - valB);
        }});

        // 分页
        const totalPages = Math.ceil(filteredAndSortedData.length / pageSize);
        if(currentPage > totalPages) currentPage = Math.max(1, totalPages);
        const startIdx = (currentPage - 1) * pageSize;
        const endIdx = startIdx + pageSize;
        const pageData = filteredAndSortedData.slice(startIdx, endIdx);

        // 更新分页信息
        document.getElementById('pageInfo').innerText = `第 ${{currentPage}} / ${{totalPages || 1}} 页 (共 ${{filteredAndSortedData.length}} 条)`;

        let html = [];
        pageData.forEach(item => {{
            let balStr = item.bal.toLocaleString('en-US', {{maximumFractionDigits: 0}});
            let pctStr = item.pct.toFixed(2) + "%";
            let chgClass = "flat", chgText = "-";
            if(item.change > 0) {{
                chgClass="up";
                chgText = "+" + item.change.toLocaleString('en-US', {{maximumFractionDigits: 0}}) + " ▲";
            }}
            else if(item.change < 0) {{
                chgClass="down";
                chgText = item.change.toLocaleString('en-US', {{maximumFractionDigits: 0}}) + " ▼";
            }}

            // BIS SWAP 净流入 = 转入 - 转出
            let bisSwapNet = item.bis_swap_in - item.bis_swap_out;
            let bisSwapNetStr = "";
            if(bisSwapNet > 0) {{
                bisSwapNetStr = `<span style="color:#4caf50">+${{bisSwapNet.toLocaleString('en-US', {{maximumFractionDigits: 0}})}}</span>`;
            }} else if(bisSwapNet < 0) {{
                bisSwapNetStr = `<span style="color:#f44336">${{bisSwapNet.toLocaleString('en-US', {{maximumFractionDigits: 0}})}}</span>`;
            }} else {{
                bisSwapNetStr = '<span style="color:#666">0</span>';
            }}

            // BIS AMM 净流入 = 转入 - 转出
            let bisAmmNet = item.bis_amm_in - item.bis_amm_out;
            let bisAmmNetStr = "";
            if(bisAmmNet > 0) {{
                bisAmmNetStr = `<span style="color:#4caf50">+${{bisAmmNet.toLocaleString('en-US', {{maximumFractionDigits: 0}})}}</span>`;
            }} else if(bisAmmNet < 0) {{
                bisAmmNetStr = `<span style="color:#f44336">${{bisAmmNet.toLocaleString('en-US', {{maximumFractionDigits: 0}})}}</span>`;
            }} else {{
                bisAmmNetStr = '<span style="color:#666">0</span>';
            }}

            // 总和 = 持仓 + BIS SWAP净额 + BIS AMM净额
            let totalBalanceStr = item.total_balance.toLocaleString('en-US', {{maximumFractionDigits: 0}});

            let tags = "";
            // 已卖完标签
            if(item.status === "SOLD_OUT") tags += "<span class='soldout-tag'>💸 已卖完</span>";
            // 流动性提供者标签
            if(item.status === "LP") tags += "<span class='lp-tag'>💧 LP</span>";
            // 交易者标签
            if(item.status === "TRADER") tags += "<span class='trader-tag'>🔄 交易</span>";
            // 新地址标签
            if(item.status === "NEW") tags += "<span class='new-tag'>🔥 NEW</span>";
            // 回归标签
            if(item.status === "RETURN") tags += "<span class='ret-tag'>♻️ 回归</span>";

            if(item.note) {{
                if(item.note.includes("MINT")) {{
                     let cleanNote = item.note.replace("🎁 [MINT] ", "");
                     tags += "<span class='mint-tag'>MINT</span>";
                     if(cleanNote) tags += "<span class='rem'>" + cleanNote + "</span> ";
                }} else {{
                     tags += "<span class='rem'>" + item.note + "</span> ";
                }}
            }}

            html.push(`
                <tr>
                    <td>#${{item.rank}}</td>
                    <td>${{tags}}<span class="addr-0x">${{item.key}}</span><span class="addr-btc">${{item.btc}}</span></td>
                    <td style="color:#fff;font-weight:bold">${{balStr}}</td>
                    <td>${{bisSwapNetStr}}</td>
                    <td>${{bisAmmNetStr}}</td>
                    <td style="color:#00bcd4;font-weight:bold">${{totalBalanceStr}}</td>
                    <td style="color:#aaa">${{pctStr}}</td>
                    <td class="${{chgClass}}">${{chgText}}</td>
                    <td><button class="btn" onclick="show('${{item.key}}')">📈</button></td>
                </tr>
            `);
        }});
        tbody.innerHTML = html.join('');
    }}

    function changePageSize() {{
        const sizes = [50, 100, 200, 500];
        const currentIdx = sizes.indexOf(pageSize);
        pageSize = sizes[(currentIdx + 1) % sizes.length];
        document.getElementById('pageSizeLabel').innerText = pageSize;
        currentPage = 1;
        render();
    }}

    function prevPage() {{
        if(currentPage > 1) {{
            currentPage--;
            render();
        }}
    }}

    function nextPage() {{
        const totalPages = Math.ceil(filteredAndSortedData.length / pageSize);
        if(currentPage < totalPages) {{
            currentPage++;
            render();
        }}
    }}

    function sort(col) {{
        if(sortCol === col) sortDesc = !sortDesc;
        else {{ sortCol = col; sortDesc = true; }}
        render();
    }}

    let myChart;
    function show(key) {{
        document.getElementById('modal').style.display='block';
        if(myChart) myChart.destroy();
        const pts = chartData[key];
        if(!pts) return;

        // 计算最大值，用于设置Y轴范围
        const maxY = Math.max(...pts.map(p=>p.y));
        const yAxisMax = maxY > 0 ? Math.ceil(maxY * 1.1) : 100;  // 留10%顶部空间

        myChart = new Chart(document.getElementById('c'), {{
            type: 'line',
            data: {{
                labels: pts.map(p=>p.t),
                datasets: [{{
                    label: '总持仓量 (包含BIS)',
                    data: pts.map(p=>p.y),
                    borderColor: '#00bcd4',
                    backgroundColor: 'rgba(0,188,212,0.1)',
                    fill: true,
                    pointRadius: 3,
                    tension: 0.1
                }}]
            }},
            options: {{
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: '地址: '+key + ' - 总持仓趋势 (包含BIS SWAP和BIS AMM)',
                        color:'#fff',
                        font:{{size:14}}
                    }},
                    legend: {{
                        labels: {{
                            color: '#ccc'
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,  // 纵坐标轴从0开始
                        min: 0,
                        max: yAxisMax,     // 根据数据动态调整最大值
                        grid: {{
                            color: '#333'
                        }},
                        ticks: {{
                            color: '#aaa'
                        }},
                        title: {{
                            display: true,
                            text: '代币数量',
                            color: '#888'
                        }}
                    }},
                    x: {{
                        grid: {{
                            color: '#333'
                        }},
                        ticks: {{
                            color: '#aaa',
                            maxTicksLimit: 10
                        }}
                    }}
                }}
            }}
        }});
    }}

    window.onclick = function(e){{if(e.target==document.getElementById('modal'))document.getElementById('modal').style.display='none';}}

    // 初始化健康度面板
    displayHealthPanel();

    render();
    </script>
    </body></html>
    """

    with open(HTML_FILE, 'w', encoding='utf-8') as f: f.write(html)
    return HTML_FILE

if __name__ == "__main__":
    db = load_db()
    minters_set = fetch_mint_list_deep()
    holders = fetch_data(minters_set, db.keys())

    if holders:
        # 进行健康度分析
        health_report = analyze_health_metrics(holders, db, minters_set)

        # 保存健康度报告到 JSON 文件
        with open('health_report.json', 'w', encoding='utf-8') as f:
            json.dump(health_report, f, indent=2, ensure_ascii=False)
        print(f"✅ 健康度报告已保存: health_report.json")

        # 生成可视化报告
        path = generate_report(holders, db, health_report)
        print(f"✅ 报告已生成: {path}")
    else:
        print("❌ 抓取失败。")
