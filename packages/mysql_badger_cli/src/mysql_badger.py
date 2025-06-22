import argparse
import re
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from datetime import datetime
import os
import numpy as np

class QueryStatistics:
    """Clasa pentru calcularea statisticilor reale - nu mai fabricăm!"""
    
    def __init__(self, values):
        self.values = sorted([v for v in values if v is not None and not pd.isna(v)])  # Sortăm și eliminăm None/NaN
        self.count = len(self.values)
    
    def min(self):
        return min(self.values) if self.values else 0
    
    def max(self):
        return max(self.values) if self.values else 0
    
    def mean(self):
        return sum(self.values) / len(self.values) if self.values else 0
    
    def median(self):
        if not self.values:
            return 0
        n = len(self.values)
        if n % 2 == 0:
            return (self.values[n//2-1] + self.values[n//2]) / 2
        return self.values[n//2]
    
    def percentile(self, p):
        """Calculează percentila p (0-100)"""
        if not self.values:
            return 0
        k = (len(self.values) - 1) * p / 100
        f = int(k)
        c = k - f
        if f == len(self.values) - 1:
            return self.values[f]
        return self.values[f] * (1 - c) + self.values[f + 1] * c
    
    def stddev(self):
        if len(self.values) < 2:
            return 0
        mean_val = self.mean()
        variance = sum((x - mean_val) ** 2 for x in self.values) / (len(self.values) - 1)
        return variance ** 0.5
    
    def variance(self):
        """Calculează varianta (standard deviation la pătrat)"""
        if len(self.values) < 2:
            return 0
        mean_val = self.mean()
        return sum((x - mean_val) ** 2 for x in self.values) / (len(self.values) - 1)
    
    def variance_to_mean_ratio(self):
        """Calculează variance-to-mean ratio (VMR) - indicator de dispersie"""
        mean_val = self.mean()
        if mean_val == 0:
            return 0
        return self.variance() / mean_val
    
    def total(self):
        return sum(self.values)

def calculate_percentage(value, total_sum):
    """Calculează procentajul real din totalul general"""
    return (value / total_sum * 100) if total_sum > 0 else 0

def format_number(value):
    """Formatează numerele mari cu k, M, etc."""
    if pd.isna(value) or value is None:
        return "0"
    if value >= 1_000_000:
        return f"{value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"{value/1_000:.1f}k"
    else:
        return f"{value:.0f}"

def format_bytes(value):
    """Formatează byte-urile"""
    if pd.isna(value) or value is None:
        return "0"
    if value >= 1024:
        return f"{value/1024:.1f}k"
    else:
        return f"{value:.0f}"

def get_detailed_stats_for_query(df, normalized_query):
    """Extrage toate statisticile pentru un query normalizat"""
    query_data = df[df['normalized_query'] == normalized_query]
    
    return {
        'query_times': query_data['query_time'].tolist(),
        'lock_times': query_data['lock_time'].tolist(),
        'rows_sent': query_data['rows_sent'].tolist(),
        'rows_examined': query_data['rows_examined'].tolist(),
        'query_lengths': [len(str(q)) for q in query_data['query'].tolist()],
        'count': len(query_data)
    }

def calculate_comprehensive_stats(df):
    """Calculează statistici comprehensive pentru toate query-urile"""
    
    # Calculăm totalurile generale pentru procentaje
    total_exec_time = df['query_time'].sum()
    total_lock_time = df['lock_time'].sum()
    total_rows_sent = df['rows_sent'].sum()
    total_rows_examined = df['rows_examined'].sum()
    total_query_count = len(df)
    
    results = []
    
    for normalized_query in df['normalized_query'].unique():
        stats_data = get_detailed_stats_for_query(df, normalized_query)
        
        # Calculăm statisticile pentru fiecare atribut
        exec_stats = QueryStatistics(stats_data['query_times'])
        lock_stats = QueryStatistics(stats_data['lock_times'])
        rows_sent_stats = QueryStatistics(stats_data['rows_sent'])
        rows_examined_stats = QueryStatistics(stats_data['rows_examined'])
        query_size_stats = QueryStatistics(stats_data['query_lengths'])
        
        result = {
            'normalized_query': normalized_query,
            'count': stats_data['count'],
            'total_time': exec_stats.total(),
            'mean_time': exec_stats.mean(),
            'max_time': exec_stats.max(),
            'mean_rows_sent': rows_sent_stats.mean(),
            'mean_rows_examined': rows_examined_stats.mean(),
            'variance_to_mean_ratio': exec_stats.variance_to_mean_ratio(),
            'stats': {
                'count': {
                    'pct': calculate_percentage(stats_data['count'], total_query_count),
                    'total': stats_data['count'],
                    'min': '-',
                    'max': '-',
                    'avg': '-',
                    'p95': '-',
                    'stddev': '-',
                    'median': '-'
                },
                'exec_time': {
                    'pct': calculate_percentage(exec_stats.total(), total_exec_time),
                    'total': f"{exec_stats.total():.3f}s",
                    'min': f"{exec_stats.min():.3f}s",
                    'max': f"{exec_stats.max():.3f}s",
                    'avg': f"{exec_stats.mean():.3f}s",
                    'p95': f"{exec_stats.percentile(95):.3f}s",
                    'stddev': f"{exec_stats.stddev():.3f}s",
                    'median': f"{exec_stats.median():.3f}s"
                },
                'lock_time': {
                    'pct': calculate_percentage(lock_stats.total(), total_lock_time) if total_lock_time > 0 else 0,
                    'total': f"{lock_stats.total():.6f}s",
                    'min': f"{lock_stats.min():.6f}s",
                    'max': f"{lock_stats.max():.6f}s",
                    'avg': f"{lock_stats.mean():.6f}s",
                    'p95': f"{lock_stats.percentile(95):.6f}s",
                    'stddev': f"{lock_stats.stddev():.6f}s",
                    'median': f"{lock_stats.median():.6f}s"
                },
                'rows_sent': {
                    'pct': calculate_percentage(rows_sent_stats.total(), total_rows_sent) if total_rows_sent > 0 else 0,
                    'total': format_number(rows_sent_stats.total()),
                    'min': format_number(rows_sent_stats.min()),
                    'max': format_number(rows_sent_stats.max()),
                    'avg': format_number(rows_sent_stats.mean()),
                    'p95': format_number(rows_sent_stats.percentile(95)),
                    'stddev': format_number(rows_sent_stats.stddev()),
                    'median': format_number(rows_sent_stats.median())
                },
                'rows_examined': {
                    'pct': calculate_percentage(rows_examined_stats.total(), total_rows_examined) if total_rows_examined > 0 else 0,
                    'total': format_number(rows_examined_stats.total()),
                    'min': format_number(rows_examined_stats.min()),
                    'max': format_number(rows_examined_stats.max()),
                    'avg': format_number(rows_examined_stats.mean()),
                    'p95': format_number(rows_examined_stats.percentile(95)),
                    'stddev': format_number(rows_examined_stats.stddev()),
                    'median': format_number(rows_examined_stats.median())
                },
                'query_size': {
                    'pct': 0,  # Procentajul din query size nu e relevant
                    'total': format_bytes(query_size_stats.total()),
                    'min': format_bytes(query_size_stats.min()),
                    'max': format_bytes(query_size_stats.max()),
                    'avg': format_bytes(query_size_stats.mean()),
                    'p95': format_bytes(query_size_stats.percentile(95)),
                    'stddev': format_bytes(query_size_stats.stddev()),
                    'median': format_bytes(query_size_stats.median())
                }
            }
        }
        results.append(result)
    
    return results

def generate_query_time_distribution(query_times):
    """
    Generează un grafic ASCII pentru distribuția timpului de query.
    Intervalele sunt: 1us, 10us, 100us, 1ms, 10ms, 100ms, 1s, 10s+
    Fiecare interval include limita inferioară (ex: 1s înseamnă >=1s și <10s)
    """
    boundaries = [0.000001, 0.00001, 0.0001, 0.001, 0.01, 0.1, 1, 10]
    labels = ['1us', '10us', '100us', '1ms', '10ms', '100ms', '1s', '10s+']
    
    # Inițializăm contoarele pentru fiecare interval
    counts = [0] * len(labels)
    total_queries = len(query_times)
    
    # Clasificăm fiecare query în intervalul corespunzător
    for t in query_times:
        # Pentru valori peste 10s
        if t >= 10:
            counts[-1] += 1
            continue
            
        # Pentru valori sub 1us
        if t < 0.000001:
            counts[0] += 1
            continue
            
        # Pentru toate celelalte valori
        for i in range(len(boundaries)-1):
            if boundaries[i] <= t < boundaries[i+1]:
                counts[i] += 1
                break
    
    # Calculăm procentajele și generăm liniile graficului
    lines = ['# Query_time distribution']
    
    # Adăugăm liniile pentru fiecare interval
    for i, (label, count) in enumerate(zip(labels, counts)):
        # Generăm linia cu spațiu fix pentru label
        line = f'# {label:>6}'
        
        # Adăugăm #-uri doar dacă avem query-uri în acest interval
        if count > 0:
            line += ' ' + '#' * 50
            
        lines.append(line)
    
    return '\n'.join(lines)

def generate_report(df, summary, top_by_time, top_by_frequency, qps_data, avg_query_time_data, output_file, log_filename=None):
    """
    Generates the HTML report from a Jinja2 template.
    """
    # Get the directory where this script is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Templates directory is one level up and then in templates/
    template_dir = os.path.join(os.path.dirname(current_dir), 'templates')
    
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('report_template.html')

    # Convert dataframes to list of dictionaries for the template
    top_by_time_dict = top_by_time.to_dict(orient='records')
    top_by_frequency_dict = top_by_frequency.to_dict(orient='records')

    # Adaugă distribuția timpului pentru fiecare query folosind toate query-urile
    for query_data in top_by_time_dict:
        normalized_query = query_data['normalized_query']
        # Luăm toate timpii pentru acest query normalizat
        all_times = df[df['normalized_query'] == normalized_query]['query_time'].tolist()
        query_data['time_distribution'] = generate_query_time_distribution(all_times)

    for query_data in top_by_frequency_dict:
        normalized_query = query_data['normalized_query']
        # Luăm toate timpii pentru acest query normalizat
        all_times = df[df['normalized_query'] == normalized_query]['query_time'].tolist()
        query_data['time_distribution'] = generate_query_time_distribution(all_times)

    # Adăugăm informațiile despre log și ora generării
    generation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_basename = os.path.basename(log_filename) if log_filename else 'Unknown'
    
    html_content = template.render(
        summary=summary,
        top_by_time=top_by_time_dict,
        top_by_frequency=top_by_frequency_dict,
        qps_data=qps_data,
        avg_query_time_data=avg_query_time_data,
        top_n=len(top_by_time_dict),
        log_filename=log_basename,
        generation_time=generation_time
    )

    with open(output_file, 'w') as f:
        f.write(html_content)
    print(f"Successfully generated report at {output_file}")

def normalize_query(query):
    """
    Normalizes a SQL query by lowercasing, replacing values with placeholders,
    and removing extra spaces.
    """
    query = query.lower()
    # Replace strings with a placeholder
    query = re.sub(r"'.*?'", "'S'", query)
    query = re.sub(r'".*?"', '"S"', query)
    # Replace numbers with a placeholder
    query = re.sub(r'\b\d+\b', 'N', query)
    # Remove extra spaces
    query = re.sub(r'\s+', ' ', query).strip()
    return query

def main():
    parser = argparse.ArgumentParser(description='MySQL Slow Query Log Analyser like pgbadger.')
    parser.add_argument('-f', '--file', help='Path to the slow query log file.', required=True)
    parser.add_argument('-o', '--output', help='Path to the output HTML report.', default='mysql-report.html')
    parser.add_argument('-t', '--top-n', type=int, default=10, help='Number of top queries to display in the report (default: 10)')
    args = parser.parse_args()

    print(f"Analysing {args.file}...")

    all_queries_data = []
    for block in parse_log_by_block(args.file):
        data = extract_query_data(block)
        if data:
            all_queries_data.append(data)
    
    if not all_queries_data:
        print("No queries found in the log file. Exiting.")
        return

    df = pd.DataFrame(all_queries_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['normalized_query'] = df['query'].apply(normalize_query)

    # Calculate QPS
    qps_df = df.set_index('timestamp')
    
    duration_seconds = 0
    if not qps_df.empty:
        duration_seconds = (qps_df.index.max() - qps_df.index.min()).total_seconds()
    
    resample_period = 's' # default to seconds (lowercase to avoid deprecation warning)
    resample_label = 'Queries per Second'
    if duration_seconds > 300: # Switch to minutes if log spans more than 5 minutes
        resample_period = 'min' # use minutes
        resample_label = 'Queries per Minute'

    qps_data = {'labels': [], 'values': [], 'label': resample_label}
    if not qps_df.empty:
        qps = qps_df.resample(resample_period).size()
        qps_data['labels'] = qps.index.strftime('%Y-%m-%d %H:%M:%S').tolist()
        qps_data['values'] = qps.values.tolist()

    # Calculate Average Query Time over time
    avg_query_time_data = {'labels': [], 'values': [], 'label': f'Average Query Time'}
    if not qps_df.empty:
        avg_time = qps_df['query_time'].resample(resample_period).mean().fillna(0)
        avg_query_time_data['labels'] = avg_time.index.strftime('%Y-%m-%d %H:%M:%S').tolist()
        avg_query_time_data['values'] = avg_time.values.tolist()

    # Prepare summary data
    summary = {
        'total_queries': len(df),
        'total_query_time': df['query_time'].sum(),
        'unique_queries': len(df['normalized_query'].unique()),
        'start_time': df['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S'),
        'end_time': df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
    }

    # Calculate comprehensive statistics using our new functions
    comprehensive_stats = calculate_comprehensive_stats(df)
    
    # Convert to DataFrame for easier manipulation
    stats_df = pd.DataFrame(comprehensive_stats)

    # Top N by total time
    top_by_time = stats_df.sort_values(by='total_time', ascending=False).head(args.top_n)
    
    def get_query_examples(normalized_query):
        query_df = df[df['normalized_query'] == normalized_query].sort_values(by='timestamp')
        
        count = len(query_df)
        if count == 0:
            return []
        
        indices_to_pick = [0]
        if count > 1:
            indices_to_pick.append(count - 1)
        if count > 2:
            indices_to_pick.insert(1, count // 2)
            
        # Ensure unique indices if count is small
        indices_to_pick = sorted(list(set(indices_to_pick)))

        examples = query_df.iloc[indices_to_pick].copy()
        examples['timestamp'] = examples['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
        return examples.to_dict(orient='records')

    top_by_time['examples'] = top_by_time['normalized_query'].apply(get_query_examples)

    # Top N by frequency
    top_by_frequency = stats_df.sort_values(by='count', ascending=False).head(args.top_n)
    top_by_frequency['examples'] = top_by_frequency['normalized_query'].apply(get_query_examples)

    generate_report(df, summary, top_by_time, top_by_frequency, qps_data, avg_query_time_data, args.output, args.file)

def extract_query_data(block):
    """
    Extracts query details from a log block using regex.
    """
    user_host_re = re.search(r'# User@Host: ([\w.-]+)(?:\[[^\]]*\])?\s*@\s*(?:\[([\w\d\._-]+)\]|([\w\d\._-]+))', block)
    query_time_re = re.search(r'# Query_time: ([\d\.]+)', block)
    lock_time_re = re.search(r'Lock_time: ([\d\.]+)', block)
    rows_sent_re = re.search(r'Rows_sent: (\d+)', block)
    rows_examined_re = re.search(r'Rows_examined: (\d+)', block)
    
    query_re = re.search(r'SET timestamp=\d+;\n(.*?)(?=# Time:|$)', block, re.DOTALL)

    # Handle multiple timestamp formats
    timestamp = None
    time_match = re.search(r'# Time: (.*)', block)
    if time_match:
        time_str = time_match.group(1).strip()
        try:
            # New format e.g. 2023-10-27T10:30:00.123456Z
            timestamp = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except ValueError:
            # Old format e.g. 231027 10:30:00
            try:
                # Replace multiple spaces between date and time
                time_str_normalized = " ".join(time_str.split())
                timestamp = datetime.strptime(time_str_normalized, '%y%m%d %H:%M:%S')
            except ValueError:
                timestamp = None # Could not parse time

    if not all([timestamp, query_time_re, lock_time_re, rows_sent_re, rows_examined_re, query_re]):
        # We can add a warning here if needed
        return None

    query = query_re.group(1).strip()
    if not query:
        return None

    user = user_host_re.group(1) if user_host_re else 'N/A'
    host = (user_host_re.group(2) or user_host_re.group(3)) if user_host_re else 'N/A'

    return {
        'timestamp': timestamp,
        'query_time': float(query_time_re.group(1)),
        'lock_time': float(lock_time_re.group(1)),
        'rows_sent': int(rows_sent_re.group(1)),
        'rows_examined': int(rows_examined_re.group(1)),
        'user': user,
        'host': host,
        'query': query
    }

def parse_log_by_block(log_file):
    """
    Parses the log file and yields one query block at a time.
    A new block starts with the '# Time:' line.
    """
    try:
        with open(log_file, 'r') as f:
            block = []
            for line in f:
                if line.startswith('# Time:') and block:
                    yield "".join(block)
                    block = [line]
                else:
                    block.append(line)
            if block:
                yield "".join(block)
    except FileNotFoundError:
        print(f"Error: File not found at {log_file}")
        exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)

if __name__ == '__main__':
    main() 