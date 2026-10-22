from content import collect
if __name__ == '__main__':
    events, months = collect()
    print(f'Content validation passed: {len(events)} public calendar entries, {len(months)} month settings.')
