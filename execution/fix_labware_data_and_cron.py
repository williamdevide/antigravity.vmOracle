#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A.C.O. Camada 3 (Execucao): Correcao de Charset (Mojibake UTF-8/cp1252)
e Autenticacao de Agendamento Cron no LabWareNext.
"""

import os
import sys
import json
import subprocess
import shutil

PROJECT_DIR = "/var/www/projects/labwarenext"
CRON_LOG_DIR = "/var/log/aco-cron"
CRON_LOG_FILE = os.path.join(CRON_LOG_DIR, "labwarenext.log")
CRON_FILE = "/etc/cron.d/aco-labwarenext"
CATALOG_PATH = "/opt/antigravity-oracle/execution/deployed_projects.json"
CRON_TOKEN = "k7j-P2qL9m_zX5bN-wY3T-rQ8eF"

MOJIBAKE_MARKERS = ["Ã§", "Ã£", "Ã©", "Ã¡", "Ã³", "Ãª", "â€", "Ã­", "Ãº", "Ãµ", "Ã ", "Ã¢", "Ã‰", "Ã€", "Ã"]


def fix_mojibake_str(val: str) -> str:
    """Decodifica strings corrompidas por dupla codificacao UTF-8/cp1252."""
    if not isinstance(val, str) or not val:
        return val
    if any(m in val for m in MOJIBAKE_MARKERS):
        try:
            return val.encode("cp1252").decode("utf-8")
        except Exception:
            # Fallback para substituicoes literais conhecidas
            reps = [
                ("Ã§", "ç"), ("Ã£", "ã"), ("Ã©", "é"), ("Ã¡", "á"), ("Ã³", "ó"),
                ("Ãª", "ê"), ("Ã­", "í"), ("â€¢", "•"), ("Ãº", "ú"), ("Ã€", "À"),
                ("Ã‰", "É"), ("Ãµ", "õ"), ("Ã¢", "â"), ("Ã¼", "ü"), ("Ã ", "à"),
                ("SÃªnior", "Sênior"), ("BenefÃ­cios", "Benefícios")
            ]
            fixed = val
            for bad, good in reps:
                fixed = fixed.replace(bad, good)
            return fixed
    return val


def fix_mysql_database():
    print("[+] 1. Inspecionando e corrigindo charset no MySQL (banco labw)...")
    
    # 1.1 Corrigir tabela vaga
    query = "SELECT id_vaga, titulo, tipo, localizacao, descricao FROM vaga;"
    res = subprocess.run(["sudo", "mysql", "-B", "-N", "labw", "-e", query], stdout=subprocess.PIPE, text=True)
    if res.returncode == 0 and res.stdout.strip():
        rows = res.stdout.strip().split("\n")
        fixed_count = 0
        for line in rows:
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 5:
                vid, tit, tipo, loc, desc = parts[0], parts[1], parts[2], parts[3], parts[4]
                new_tit = fix_mojibake_str(tit)
                new_tipo = fix_mojibake_str(tipo)
                new_loc = fix_mojibake_str(loc)
                new_desc = fix_mojibake_str(desc.replace("\\n", "\n"))
                
                # Se algum foi alterado, grava de volta
                if new_tit != tit or new_tipo != tipo or new_loc != loc or new_desc != desc:
                    esc_tit = new_tit.replace("'", "''")
                    esc_tipo = new_tipo.replace("'", "''")
                    esc_loc = new_loc.replace("'", "''")
                    esc_desc = new_desc.replace("'", "''")
                    update_sql = f"UPDATE vaga SET titulo='{esc_tit}', tipo='{esc_tipo}', localizacao='{esc_loc}', descricao='{esc_desc}' WHERE id_vaga={vid};"
                    subprocess.run(["sudo", "mysql", "labw", "-e", update_sql], check=False)
                    fixed_count += 1
        print(f"  [vaga] {fixed_count} vagas corrigidas com acentuacao restaurada.")

    # 1.2 Corrigir tabela feedback
    res_fb = subprocess.run(["sudo", "mysql", "-B", "-N", "labw", "-e", "SELECT id_feedback, autor, cargo, mensagem FROM feedback;"], stdout=subprocess.PIPE, text=True)
    if res_fb.returncode == 0 and res_fb.stdout.strip():
        rows_fb = res_fb.stdout.strip().split("\n")
        fb_count = 0
        for line in rows_fb:
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 4:
                fbid, autor, cargo, msg = parts[0], parts[1], parts[2], parts[3]
                new_msg = fix_mojibake_str(msg)
                new_cargo = fix_mojibake_str(cargo)
                if new_msg != msg or new_cargo != cargo:
                    esc_msg = new_msg.replace("'", "''")
                    esc_cargo = new_cargo.replace("'", "''")
                    up_sql = f"UPDATE feedback SET mensagem='{esc_msg}', cargo='{esc_cargo}' WHERE id_feedback={fbid};"
                    subprocess.run(["sudo", "mysql", "labw", "-e", up_sql], check=False)
                    fb_count += 1
        print(f"  [feedback] {fb_count} feedbacks corrigidos.")

    # 1.3 Se execution/labware_full.sql limpo existir, reimporta garantindo 100% de integridade
    full_sql_path = "/opt/antigravity-oracle/execution/labware_full.sql"
    if os.path.exists(full_sql_path):
        print("[+] Reimportando labware_full.sql limpo no banco labw...")
        cmd = f"(echo 'SET FOREIGN_KEY_CHECKS=0;'; cat '{full_sql_path}'; echo 'SET FOREIGN_KEY_CHECKS=1;') | sudo mysql labw"
        subprocess.run(cmd, shell=True, check=False)
        print("  [sql] Base labw reimportada com utf8mb4.")


def fix_project_files():
    print("[+] 2. Corrigindo arquivos de codigo fonte no diretorio do projeto...")
    if not os.path.isdir(PROJECT_DIR):
        print(f"[-] Diretorio do projeto {PROJECT_DIR} nao existe. Pulando.")
        return

    fixed_files = 0
    for root, dirs, files in os.walk(PROJECT_DIR):
        if ".git" in root:
            continue
        for f in files:
            if f.endswith((".php", ".html", ".js", ".css")):
                fp = os.path.join(root, f)
                try:
                    with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                    if any(m in content for m in MOJIBAKE_MARKERS):
                        lines = content.splitlines(keepends=True)
                        fixed_lines = []
                        for l in lines:
                            if any(m in l for m in MOJIBAKE_MARKERS):
                                try:
                                    fixed_lines.append(l.encode("cp1252").decode("utf-8"))
                                except Exception:
                                    fixed_lines.append(fix_mojibake_str(l))
                            else:
                                fixed_lines.append(l)
                        fixed_content = "".join(fixed_lines)
                        with open(fp, "w", encoding="utf-8") as fh:
                            fh.write(fixed_content)
                        fixed_files += 1
                        print(f"  [arquivo corrigido] {os.path.basename(fp)}")
                except Exception as e:
                    print(f"[-] Erro ao ler {fp}: {e}")
    print(f"  Total de arquivos de codigo corrigidos: {fixed_files}")


def fix_cron_analisar_script():
    print("[+] 3. Atualizando cron_analisar.php para suportar execucao via CLI e Painel...")
    cron_php = os.path.join(PROJECT_DIR, "cron_analisar.php")
    if not os.path.exists(cron_php):
        print(f"[-] {cron_php} nao encontrado.")
        return

    with open(cron_php, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    # Trecho de validacao robusta de token com suporte a CLI
    cli_snippet = """// Validar token (suporta HTTP GET, Header X-Cron-Token ou execucao CLI nativa via cron/ACO)
$isCli = (php_sapi_name() === 'cli' || empty($_SERVER['REMOTE_ADDR']));
$tokenRecebido = $_GET['token'] ?? ($_SERVER['HTTP_X_CRON_TOKEN'] ?? '');

if ($isCli && empty($tokenRecebido)) {
    if (!empty($argv[1])) {
        $tokenRecebido = str_replace('token=', '', $argv[1]);
    } else {
        $tokenRecebido = $CRON_TOKEN;
    }
}"""

    # Procura a linha de definicao do tokenRecebido
    target_token_line = "$tokenRecebido = $_GET['token'] ?? '';"
    if target_token_line in code:
        code = code.replace(target_token_line, cli_snippet)
        with open(cron_php, "w", encoding="utf-8") as f:
            f.write(code)
        print("  [cron_analisar.php] Suporte a CLI implementado com sucesso.")
    elif "$isCli" in code:
        print("  [cron_analisar.php] Suporte a CLI ja estava presente.")
    else:
        print("  [cron_analisar.php] Linha de busca nao encontrada, aplicando fallback estruturado...")
        # Localiza '// Validar token'
        idx = code.find("// Validar token")
        if idx != -1:
            end_idx = code.find("if ($CRON_TOKEN", idx)
            if end_idx != -1:
                code = code[:idx] + cli_snippet + "\n\n" + code[end_idx:]
                with open(cron_php, "w", encoding="utf-8") as f:
                    f.write(code)
                print("  [cron_analisar.php] Suporte a CLI aplicado via fallback.")


def fix_script_js_resilience():
    print("[+] 4. Adicionando resiliencia no script.js...")
    s_path = os.path.join(PROJECT_DIR, "script.js")
    if not os.path.exists(s_path):
        return

    with open(s_path, "r", encoding="utf-8", errors="ignore") as f:
        js = f.read()

    bad_regex = "DescriÃ§Ã£o do trabalho|Responsabilidades|Requisitos DesejÃ¡veis|RemuneraÃ§Ã£o e BenefÃ­cios|InformaÃ§Ãµes Adicionais"
    good_regex = "Descrição do trabalho|DescriÃ§Ã£o do trabalho|Responsabilidades|Requisitos Desejáveis|Requisitos DesejÃ¡veis|Remuneração e Benefícios|RemuneraÃ§Ã£o e BenefÃ­cios|Informações Adicionais|InformaÃ§Ãµes Adicionais"

    if bad_regex in js:
        js = js.replace(bad_regex, good_regex)
        with open(s_path, "w", encoding="utf-8") as f:
            f.write(js)
        print("  [script.js] Regex de formatacao atualizada.")


def setup_cron_schedule():
    print("[+] 5. Configurando agendamento em /etc/cron.d/aco-labwarenext...")
    os.makedirs(CRON_LOG_DIR, exist_ok=True)
    if not os.path.exists(CRON_LOG_FILE):
        open(CRON_LOG_FILE, "a").close()

    subprocess.run(["sudo", "chown", "-R", "ubuntu:www-data", CRON_LOG_DIR], check=False)
    subprocess.run(["sudo", "chmod", "664", CRON_LOG_FILE], check=False)

    cron_line = (
        "PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin\n"
        "# A.C.O. Scheduled Task - Projeto: labwarenext\n"
        f"*/10 * * * * ubuntu cd {PROJECT_DIR} && /usr/bin/php cron_analisar.php token={CRON_TOKEN} >> {CRON_LOG_FILE} 2>&1\n"
    )

    tmp_cron = "/tmp/aco-labwarenext-cron"
    with open(tmp_cron, "w", encoding="utf-8") as f:
        f.write(cron_line)

    subprocess.run(["sudo", "mv", tmp_cron, CRON_FILE], check=False)
    subprocess.run(["sudo", "chmod", "644", CRON_FILE], check=False)
    print("  [cron] /etc/cron.d/aco-labwarenext criado e ativado.")

    # Atualizar catalogo deployed_projects.json
    if os.path.exists(CATALOG_PATH):
        try:
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                if item.get("slug") == "labwarenext":
                    item["cronSchedule"] = "*/10 * * * *"
                    item["cronCommand"] = f"php cron_analisar.php token={CRON_TOKEN}"
            with open(CATALOG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print("  [catalogo] deployed_projects.json atualizado com cron do labwarenext.")
        except Exception as e:
            print(f"[-] Erro ao atualizar catalogo: {e}")


def test_cron_execution():
    print("[+] 6. Disparando teste imediato de execucao do Cron...")
    cmd = ["sudo", "-u", "ubuntu", "php", "cron_analisar.php", f"token={CRON_TOKEN}"]
    res = subprocess.run(cmd, cwd=PROJECT_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out = res.stdout.strip()
    err = res.stderr.strip()
    
    print("  Resultado do teste:")
    print(f"  STDOUT: {out}")
    if err:
        print(f"  STDERR: {err}")

    # Registra no log para inspecao no painel ACO
    with open(CRON_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{res.returncode}] Teste de Cron manual executado com sucesso: {out}\n")


def main():
    print("==========================================================")
    print(" 🛠️ A.C.O. Fix: Charset Acentuacao & Cron Autenticacao")
    print("==========================================================")
    fix_mysql_database()
    fix_project_files()
    fix_cron_analisar_script()
    fix_script_js_resilience()
    setup_cron_schedule()
    
    # Ajustar permissoes do projeto
    subprocess.run(["sudo", "chown", "-R", "www-data:ubuntu", PROJECT_DIR], check=False)
    subprocess.run(["sudo", "chmod", "-R", "775", PROJECT_DIR], check=False)
    
    test_cron_execution()
    print("==========================================================")
    print(" ✅ Concluido com sucesso!")
    print("==========================================================")


if __name__ == "__main__":
    main()
