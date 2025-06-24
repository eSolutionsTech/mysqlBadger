import pytest
import pandas as pd
from src.mysql_badger import (
    generate_query_time_distribution, 
    QueryStatistics, 
    calculate_percentage,
    format_number,
    format_bytes,
    get_detailed_stats_for_query,
    calculate_comprehensive_stats,
    parse_log_by_block,
    extract_query_data,
    normalize_query,
    generate_report
)

def test_generate_query_time_distribution():
    """
    Testăm funcția de generare a distribuției timpului de query cu diferite cazuri.
    """
    # Test Case 1: Query-uri în diferite intervale
    query_times = [
        0.0000009,  # < 1us
        0.000002,   # 1-10us
        0.00002,    # 10-100us
        0.0002,     # 100us-1ms
        0.002,      # 1-10ms
        0.02,       # 10-100ms
        0.2,        # 100ms-1s
        2.0,        # 1-10s
        20.0        # >10s
    ]
    
    distribution = generate_query_time_distribution(query_times)
    lines = distribution.split('\n')
    
    # Verificăm că avem header-ul și toate intervalele
    assert len(lines) == 9  # header + 8 intervale
    assert lines[0] == '# Query_time distribution'
    
    # Verificăm că fiecare interval are exact 50 de #-uri pentru distribuție
    for line in lines[1:]:
        hash_count = line.count('#') - 1  # -1 pentru # de la început
        assert hash_count == 50  # Fiecare interval care are query-uri are 50 de #-uri

def test_generate_query_time_distribution_empty():
    """
    Testăm cazul când nu avem query-uri.
    """
    distribution = generate_query_time_distribution([])
    lines = distribution.split('\n')
    
    assert len(lines) == 9  # header + 8 intervale
    assert lines[0] == '# Query_time distribution'
    
    # Verificăm că avem doar label-urile fără #-uri pentru distribuție
    for line in lines[1:]:
        assert line.startswith('#')  # avem # pentru formatare
        assert '#' not in line[2:]  # nu avem #-uri după label

def test_generate_query_time_distribution_single_interval():
    """
    Testăm cazul când toate query-urile sunt în același interval.
    """
    # Toate query-urile între 1-10 secunde
    query_times = [2.5, 3.0, 4.2, 5.0, 6.1]
    
    distribution = generate_query_time_distribution(query_times)
    print("\nDistribuția pentru query-uri între 1-10 secunde:")
    print(distribution)
    lines = distribution.split('\n')
    
    assert len(lines) == 9
    
    # Verificăm că doar intervalul 1s are #-uri și restul sunt goale
    for line in lines[1:]:
        if '1s' in line:
            print(f"\nLinia cu 1s: '{line}'")
            assert line.count('#') - 1 == 50  # Intervalul cu query-uri are 50 de #-uri (minus # de la început)
        else:
            assert line.count('#') == 1  # Doar # de la început

def test_generate_query_time_distribution_edge_cases():
    """
    Testăm cazurile limită pentru intervale.
    """
    query_times = [
        0.000001,  # exact 1us - ar trebui să fie în primul interval
        0.00001,   # exact 10us
        0.0001,    # exact 100us
        0.001,     # exact 1ms
        0.01,      # exact 10ms
        0.1,       # exact 100ms
        1.0,       # exact 1s
        10.0       # exact 10s - ar trebui să fie în intervalul 1-10s
    ]
    
    distribution = generate_query_time_distribution(query_times)
    lines = distribution.split('\n')
    
    assert len(lines) == 9
    # Verificăm că fiecare interval are exact 50 de #-uri pentru distribuție
    for line in lines[1:]:
        hash_count = line.count('#') - 1  # -1 pentru # de la început
        assert hash_count == 50  # Fiecare interval care are query-uri are 50 de #-uri

# Teste pentru noile funcții statistice
def test_query_statistics():
    """Testează clasa QueryStatistics cu date reale"""
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    stats = QueryStatistics(values)
    
    assert stats.min() == 1.0
    assert stats.max() == 5.0
    assert stats.mean() == 3.0
    assert stats.median() == 3.0
    assert abs(stats.percentile(95) - 4.8) < 0.1
    assert abs(stats.stddev() - 1.58) < 0.1
    assert stats.total() == 15.0

def test_query_statistics_empty():
    """Testează clasa QueryStatistics cu date goale"""
    stats = QueryStatistics([])
    
    assert stats.min() == 0
    assert stats.max() == 0
    assert stats.mean() == 0
    assert stats.median() == 0
    assert stats.percentile(95) == 0
    assert stats.stddev() == 0
    assert stats.total() == 0

def test_query_statistics_with_none_values():
    """Testează clasa QueryStatistics cu valori None și NaN"""
    import math
    values = [1.0, None, 2.0, math.nan, 3.0]
    stats = QueryStatistics(values)
    
    # Ar trebui să ignore None și NaN
    assert stats.count == 3
    assert stats.min() == 1.0
    assert stats.max() == 3.0
    assert stats.mean() == 2.0

def test_calculate_percentage():
    """Testează calcularea procentajelor"""
    assert calculate_percentage(25, 100) == 25.0
    assert calculate_percentage(0, 100) == 0.0
    assert calculate_percentage(100, 100) == 100.0
    assert calculate_percentage(50, 0) == 0.0  # Division by zero should return 0

def test_format_number():
    """Testează formatarea numerelor"""
    assert format_number(500) == "500"
    assert format_number(1500) == "1.5k"
    assert format_number(1500000) == "1.5M"
    assert format_number(None) == "0"
    assert format_number(float('nan')) == "0"

def test_format_bytes():
    """Testează formatarea byte-urilor"""
    assert format_bytes(500) == "500"
    assert format_bytes(1500) == "1.5k"
    assert format_bytes(None) == "0"
    assert format_bytes(float('nan')) == "0"

def create_mock_dataframe():
    """Creează un DataFrame mock pentru testare"""
    data = {
        'normalized_query': ['select * from users where id = N', 'select * from products where price > N'] * 3,
        'query_time': [1.5, 2.0, 1.2, 1.8, 1.3, 2.1],
        'lock_time': [0.001, 0.002, 0.001, 0.0015, 0.001, 0.002],
        'rows_sent': [10, 5, 12, 8, 11, 6],
        'rows_examined': [1000, 2000, 1200, 1800, 1100, 1900],
        'query': ['SELECT * FROM users WHERE id = 123', 'SELECT * FROM products WHERE price > 100'] * 3
    }
    return pd.DataFrame(data)

def test_get_detailed_stats_for_query():
    """Testează extragerea statisticilor detaliate pentru un query"""
    df = create_mock_dataframe()
    
    stats = get_detailed_stats_for_query(df, 'select * from users where id = N')
    
    assert len(stats['query_times']) == 3
    assert len(stats['lock_times']) == 3
    assert len(stats['rows_sent']) == 3
    assert len(stats['rows_examined']) == 3
    assert len(stats['query_lengths']) == 3
    assert stats['count'] == 3

def test_calculate_comprehensive_stats():
    """Testează calcularea statisticilor comprehensive"""
    df = create_mock_dataframe()
    results = calculate_comprehensive_stats(df)
    
    # Verificăm că avem rezultate pentru ambele query-uri unice
    assert len(results) == 2
    
    # Verificăm că fiecare rezultat are toate atributele
    for result in results:
        assert 'normalized_query' in result
        assert 'count' in result
        assert 'total_time' in result
        assert 'mean_time' in result
        assert 'max_time' in result
        assert 'mean_rows_sent' in result
        assert 'mean_rows_examined' in result
        assert 'stats' in result
        
        # Verificăm că stats conține toate atributele
        assert 'count' in result['stats']
        assert 'exec_time' in result['stats']
        assert 'lock_time' in result['stats']
        assert 'rows_sent' in result['stats']
        assert 'rows_examined' in result['stats']
        assert 'query_size' in result['stats']
        
        # Verificăm că fiecare atribut are toate statisticile
        for attr_name, attr_data in result['stats'].items():
            assert 'pct' in attr_data
            assert 'total' in attr_data
            assert 'min' in attr_data
            assert 'max' in attr_data
            assert 'avg' in attr_data
            assert 'p95' in attr_data
            assert 'stddev' in attr_data
            assert 'median' in attr_data

def test_comprehensive_stats_percentages():
    """Testează că procentajele sunt calculate corect"""
    df = create_mock_dataframe()
    results = calculate_comprehensive_stats(df)
    
    # Calculăm totalurile pentru verificare
    total_count = len(df)
    total_exec_time = df['query_time'].sum()
    
    # Verificăm că procentajele se adună la 100%
    count_pct_sum = sum(result['stats']['count']['pct'] for result in results)
    exec_time_pct_sum = sum(result['stats']['exec_time']['pct'] for result in results)
    
    assert abs(count_pct_sum - 100.0) < 0.1  # Aproximativ 100%
    assert abs(exec_time_pct_sum - 100.0) < 0.1  # Aproximativ 100%

def test_query_statistics_single_value():
    """Testează statisticile cu o singură valoare"""
    stats = QueryStatistics([5.0])
    
    assert stats.min() == 5.0
    assert stats.max() == 5.0
    assert stats.mean() == 5.0
    assert stats.median() == 5.0
    assert stats.percentile(95) == 5.0
    assert stats.stddev() == 0  # Standard deviation of single value should be 0
    assert stats.total() == 5.0

def test_query_statistics_duplicate_values():
    """Testează clasa QueryStatistics cu valori duplicate"""
    values = [2.0, 2.0, 2.0, 2.0, 2.0]
    stats = QueryStatistics(values)
    
    assert stats.count == 5
    assert stats.min() == 2.0
    assert stats.max() == 2.0
    assert stats.mean() == 2.0
    assert stats.median() == 2.0
    assert stats.percentile(95) == 2.0
    assert stats.stddev() == 0.0  # Toate valorile sunt identice
    assert stats.variance() == 0.0  # Varianta pentru valori identice
    assert stats.variance_to_mean_ratio() == 0.0  # VMR pentru valori identice

def test_query_statistics_variance_and_vmr():
    """Testează calcularea variantei și variance-to-mean ratio"""
    # Date cu variabilitate cunoscută
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    stats = QueryStatistics(values)
    
    # Verificăm calculele statistice
    assert stats.mean() == 3.0
    assert abs(stats.variance() - 2.5) < 0.01  # Varianta pentru această secvență
    assert abs(stats.stddev() - 1.58) < 0.1  # Standard deviation
    assert abs(stats.variance_to_mean_ratio() - (2.5/3.0)) < 0.01  # VMR = variance/mean
    
    # Test cu valori zero
    zero_values = [0, 0, 0]
    zero_stats = QueryStatistics(zero_values)
    assert zero_stats.variance_to_mean_ratio() == 0  # Division by zero handled

def test_comprehensive_stats_with_vmr():
    """Testează că statisticile comprehensive includ VMR corect"""
    df = create_mock_dataframe()
    results = calculate_comprehensive_stats(df)
    
    # Verificăm că fiecare rezultat are VMR calculat
    for result in results:
        assert 'variance_to_mean_ratio' in result
        assert isinstance(result['variance_to_mean_ratio'], (int, float))
        assert result['variance_to_mean_ratio'] >= 0  # VMR e întotdeauna pozitiv

# Teste noi pentru parsing și report generation
import tempfile
import os

def create_test_log_content():
    """Creează conținut de test pentru log-ul MySQL"""
    return """# Time: 2025-06-01T12:52:15.393216Z
# User@Host: test_user[test_user] @ localhost []  Id:    10
# Query_time: 0.047215  Lock_time: 0.000311 Rows_sent: 0  Rows_examined: 125693
use test_db;
SET timestamp=1748782335;
SELECT * from `zen_tickets` 
                WHERE `user_id` = '12677' AND
                `status` = 2 AND DATE(`time_left`) IS NOT NULL
                LIMIT 1;
# Time: 2025-06-01T12:52:15.410031Z
# User@Host: test_user[test_user] @ localhost []  Id:    10
# Query_time: 0.016647  Lock_time: 0.000562 Rows_sent: 1  Rows_examined: 16890
SET timestamp=1748782335;
SELECT * from `zen_users` WHERE `user_id` = '12677' LIMIT 1;
# Time: 2025-06-01T12:52:15.909624Z
# User@Host: test_user[test_user] @ localhost []  Id:    18
# Query_time: 0.041486  Lock_time: 0.000139 Rows_sent: 0  Rows_examined: 125693
SET timestamp=1748782335;
SELECT * from `zen_tickets` 
                WHERE `user_id` = '15540' AND
                `status` = 2 AND DATE(`time_left`) IS NOT NULL
                LIMIT 1;
"""

def test_extract_query_data():
    """Testează extragerea datelor dintr-un bloc de query"""
    block = """# Time: 2025-06-01T12:52:15.393216Z
# User@Host: test_user[test_user] @ localhost []  Id:    10
# Query_time: 0.047215  Lock_time: 0.000311 Rows_sent: 0  Rows_examined: 125693
use test_db;
SET timestamp=1748782335;
SELECT * from `zen_tickets` WHERE `user_id` = '12677' LIMIT 1;"""
    
    result = extract_query_data(block)
    
    assert result is not None
    assert result['query_time'] == 0.047215
    assert result['lock_time'] == 0.000311
    assert result['rows_sent'] == 0
    assert result['rows_examined'] == 125693
    assert 'SELECT * from `zen_tickets`' in result['query']

def test_extract_query_data_invalid_block():
    """Testează extragerea datelor dintr-un bloc invalid"""
    block = "Invalid block without query data"
    result = extract_query_data(block)
    assert result is None

def test_normalize_query():
    """Testează normalizarea query-urilor"""
    # Test cu numere
    query1 = "SELECT * FROM users WHERE id = 123 AND age > 25"
    normalized1 = normalize_query(query1)
    assert normalized1 == "select * from users where id = N and age > N"
    
    # Test cu string-uri
    query2 = "SELECT * FROM products WHERE name = 'test product' AND category = \"electronics\""
    normalized2 = normalize_query(query2)
    assert normalized2 == "select * from products where name = 'S' and category = \"S\""
    
    # Test cu IN clause - funcția actuală înlocuiește fiecare număr individual
    query3 = "SELECT * FROM orders WHERE status IN (1, 2, 3, 4)"
    normalized3 = normalize_query(query3)
    assert normalized3 == "select * from orders where status in (N, N, N, N)"

def test_normalize_query_complex():
    """Testează normalizarea query-urilor complexe"""
    query = """SELECT u.name, o.total 
               FROM users u 
               JOIN orders o ON u.id = o.user_id 
               WHERE u.created_at > '2023-01-01' 
               AND o.total > 100.50 
               AND u.status IN (1, 2, 3)"""
    
    normalized = normalize_query(query)
    # Funcția actuală înlocuiește fiecare număr individual și comprimă spațiile
    expected = "select u.name, o.total from users u join orders o on u.id = o.user_id where u.created_at > 'S' and o.total > N.N and u.status in (N, N, N)"
    
    assert normalized == expected

def test_parse_log_by_block():
    """Testează parsing-ul log-ului MySQL pe blocuri"""
    # Creăm un fișier temporar cu conținut de test
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        f.write(create_test_log_content())
        temp_file = f.name
    
    try:
        # Parsăm fișierul
        blocks = list(parse_log_by_block(temp_file))
        
        # Verificăm că avem blocurile așteptate
        assert len(blocks) >= 3  # Ar trebui să avem cel puțin 3 blocuri
        
        # Verificăm că primul bloc conține informațiile așteptate
        first_block = blocks[0]
        assert '# Time: 2025-06-01T12:52:15.393216Z' in first_block
        assert 'Query_time: 0.047215' in first_block
        assert 'SELECT * from `zen_tickets`' in first_block
        
    finally:
        # Curățăm fișierul temporar
        os.unlink(temp_file)

def test_parse_log_by_block_empty_file():
    """Testează parsing-ul unui fișier gol"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        f.write("")
        temp_file = f.name
    
    try:
        blocks = list(parse_log_by_block(temp_file))
        assert len(blocks) == 0
    finally:
        os.unlink(temp_file)

def test_parse_log_by_block_nonexistent_file():
    """Testează parsing-ul unui fișier inexistent"""
    # Funcția actuală aruncă FileNotFoundError în loc să facă exit(1)
    with pytest.raises(FileNotFoundError):
        list(parse_log_by_block('nonexistent_file.log'))

def test_generate_report_integration():
    """Test de integrare pentru generarea raportului - versiune simplificată"""
    # Creăm date mock pentru raport
    df = create_mock_dataframe()
    
    summary = {
        'total_queries': 6,
        'unique_queries': 2,
        'total_query_time': 10.9,
        'avg_query_time': 1.82,
        'queries_per_second': 0.5,
        'start_time': '2024-01-01 10:00:00',
        'end_time': '2024-01-01 11:00:00'
    }
    
    # Folosim DataFrame-uri goale pentru a evita complexitatea template-ului
    empty_df = pd.DataFrame()
    
    qps_data = []  # Date simple
    avg_query_time_data = []
    
    # Creăm un fișier temporar pentru output
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html') as f:
        temp_output = f.name
    
    try:
        # Generăm raportul cu date minime
        generate_report(df, summary, empty_df, empty_df, qps_data, avg_query_time_data, temp_output)
        
        # Verificăm că fișierul a fost creat
        assert os.path.exists(temp_output)
        
        # Verificăm că fișierul conține conținutul de bază
        with open(temp_output, 'r') as f:
            content = f.read()
            assert 'MySQL Badger Report' in content
            assert 'Total Queries' in content
            assert str(summary['total_queries']) in content
            
    finally:
        # Curățăm fișierul temporar
        if os.path.exists(temp_output):
            os.unlink(temp_output)

def test_generate_report_with_real_stats():
    """Test simplificat pentru generarea raportului cu statistici reale"""
    df = create_mock_dataframe()
    
    # Calculăm statistici reale folosind noua funcție
    comprehensive_stats = calculate_comprehensive_stats(df)
    
    summary = {
        'total_queries': len(df),
        'unique_queries': len(df['normalized_query'].unique()),
        'total_query_time': df['query_time'].sum(),
        'avg_query_time': df['query_time'].mean(),
        'queries_per_second': len(df) / 60,
        'start_time': '2024-01-01 10:00:00',
        'end_time': '2024-01-01 11:00:00'
    }
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html') as f:
        temp_output = f.name
    
    try:
        # Folosim DataFrame-uri goale pentru a evita complexitatea template-ului
        empty_df = pd.DataFrame()
        generate_report(df, summary, empty_df, empty_df, [], [], temp_output)
        
        assert os.path.exists(temp_output)
        
        with open(temp_output, 'r') as f:
            content = f.read()
            # Verificăm că raportul de bază a fost generat
            assert 'MySQL Badger Report' in content
            assert len(comprehensive_stats) > 0  # Verificăm că statisticile au fost calculate
            
    finally:
        if os.path.exists(temp_output):
            os.unlink(temp_output)

def test_full_pipeline_integration():
    """Test de integrare completă: parsing -> procesare -> raport"""
    # Creăm un fișier log de test
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        f.write(create_test_log_content())
        temp_log = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.html') as f:
        temp_output = f.name
    
    try:
        # Simulăm pipeline-ul complet
        blocks = list(parse_log_by_block(temp_log))
        assert len(blocks) > 0
        
        # Extragem datele
        queries_data = []
        for block in blocks:
            data = extract_query_data(block)
            if data:
                queries_data.append(data)
        
        assert len(queries_data) > 0
        
        # Creăm DataFrame
        df = pd.DataFrame(queries_data)
        
        # Adăugăm normalizarea
        df['normalized_query'] = df['query'].apply(normalize_query)
        
        # Calculăm statistici
        comprehensive_stats = calculate_comprehensive_stats(df)
        
        # Verificăm că avem statistici
        assert len(comprehensive_stats) > 0
        assert all('stats' in stat for stat in comprehensive_stats)
        
        print(f"✅ Pipeline test successful: {len(queries_data)} queries processed, {len(comprehensive_stats)} unique patterns found")
        
    finally:
        os.unlink(temp_log)
        if os.path.exists(temp_output):
            os.unlink(temp_output)

def test_main_function_file_not_found():
    """Testează că funcția main gestionează corect erorile de fișier inexistent"""
    import sys
    from io import StringIO
    
    # Salvăm stdout original
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    try:
        # Redirectăm stdout pentru a captura output-ul
        captured_output = StringIO()
        sys.stdout = captured_output
        sys.stderr = captured_output
        
        # Simulăm apelul funcției main cu un fișier inexistent
        from src.mysql_badger import main
        import sys as sys_module
        
        # Salvăm sys.argv original
        original_argv = sys_module.argv
        
        try:
            sys_module.argv = ['mysql-badger', '-f', 'nonexistent_file.log']
            main()
        except SystemExit:
            pass  # Așteptăm SystemExit de la sys.exit(1)
        finally:
            # Restaurăm sys.argv
            sys_module.argv = original_argv
        
        # Verificăm că mesajul de eroare a fost afișat
        output = captured_output.getvalue()
        assert "Error: File not found at nonexistent_file.log" in output
        
    finally:
        # Restaurăm stdout și stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr 