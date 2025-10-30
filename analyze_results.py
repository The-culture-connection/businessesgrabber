import pandas as pd

df = pd.read_excel('improved_businesses.xlsx', sheet_name='All Businesses')

print(f'Total businesses: {len(df)}')
print(f'\nColumns: {list(df.columns)}')
print(f'\nFirst 3 businesses:')
print(df[['Name', 'Category', 'Phone', 'Address', 'City', 'State', 'Zip']].head(3).to_string())

print(f'\n\nContact Info Summary:')
print(f'With email: {(df["Email"] != "").sum()}')
print(f'With phone: {(df["Phone"] != "").sum()}')
print(f'With address: {(df["Address"] != "").sum()}')
print(f'With website: {(df["Website"] != "").sum()}')

print(f'\n\nCategories found:')
for cat in df['Category'].unique():
    if cat:
        count = (df['Category'] == cat).sum()
        print(f'  - {cat}: {count} business(es)')

print(f'\n\nAll business names:')
for i, name in enumerate(df['Name'], 1):
    print(f'{i}. {name}')
