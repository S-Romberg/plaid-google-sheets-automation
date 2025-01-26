from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from plaid_sync import PlaidTransactionSync
import os

class SheetsSyncer:
    def __init__(self):
        # Google Sheets setup
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file(
            'path/to/service-account.json',
            scopes=SCOPES
        )
        self.service = build('sheets', 'v4', credentials=creds)
        self.spreadsheet_id = os.getenv('SPREADSHEET_ID')
        
        # Initialize Plaid syncer
        self.plaid_syncer = PlaidTransactionSync()

    def append_transactions(self, transactions):
        """Append transactions to Google Sheet"""
        values = [
            self.plaid_syncer.format_transaction(transaction)
            for transaction in transactions
        ]
        
        if not values:
            return
            
        body = {
            'values': values
        }
        
        try:
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range='Transactions!A:H',  # Adjust range as needed
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
        except Exception as e:
            print(f"Error appending to sheet: {e}")

def main():
    syncer = SheetsSyncer()
    
    # List of access tokens for your connected bank accounts
    access_tokens = [
        os.getenv('PLAID_ACCESS_TOKEN_1'),
        os.getenv('PLAID_ACCESS_TOKEN_2'),
        os.getenv('PLAID_ACCESS_TOKEN_3')
    ]
    
    for token in access_tokens:
        # Get new/modified transactions
        transactions = syncer.plaid_syncer.sync_transactions(token)
        # Append to Google Sheet
        syncer.append_transactions(transactions)

if __name__ == "__main__":
    main()