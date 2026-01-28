import json
import sys

def main():
    if len(sys.argv) < 2:
        print("0,0,1")
        return

    json_file = sys.argv[1]
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
            
        m = data.get('metrics', {})
        
        def get_val(key, subkey='value'):
            if key not in m: return 0
            if 'values' in m[key]: return m[key]['values'].get(subkey, 0)
            return m[key].get(subkey, 0)

        rps = get_val('http_reqs', 'rate')
        p99 = get_val('http_req_duration', 'p(99)')
        fails = get_val('http_req_failed', 'rate') # 0 is good
        
        # In k6, http_req_failed rate is 0 to 1. 1 means 100% fail.
        # We want to report fail rate.
        
        print(f"{rps},{p99},{fails}")
        
    except Exception as e:
        # sys.stderr.write(str(e))
        print("0,0,1")

if __name__ == "__main__":
    main()
