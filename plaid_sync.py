import plaid
from plaid.api import plaid_api
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.transactions_sync_request_options import TransactionsSyncRequestOptions
import os
from datetime import datetime
import json
from typing import Dict, List

class PlaidTransactionSync:
    def __init__(self):
        configuration = plaid.Configuration(
            host=plaid.Environment.Development,
            api_key={
                'clientId': os.getenv('PLAID_CLIENT_ID'),
                'secret': os.getenv('PLAID_SECRET'),
            }
        )
        
        self.client = plaid_api.PlaidApi(configuration)
        
        # Load or initialize cursor storage
        self.cursor_file = 'cursors.json'
        self.cursors = self.load_cursors()

    def load_cursors(self) -> Dict[str, str]:
        """Load cursors from file or return empty dict if file doesn't exist"""
        try:
            with open(self.cursor_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_cursors(self):
        """Save cursors to file"""
        with open(self.cursor_file, 'w') as f:
            json.dump(self.cursors, f)

    def sync_transactions(self, access_token: str) -> List[dict]:
        """
        Sync transactions for a specific access token using the cursor-based sync endpoint
        """
        has_more = True
        all_transactions = []
        cursor = self.cursors.get(access_token)

        while has_more:
            request = TransactionsSyncRequest(
                access_token=access_token,
                cursor=cursor,
                options=TransactionsSyncRequestOptions(
                    include_personal_finance_category=True
                )
            )
            
            try:
                response = self.client.transactions_sync(request)
                
                # Add new transactions
                all_transactions.extend(response['added'])
                
                # Handle modified transactions
                for modified_transaction in response['modified']:
                    # Update existing transaction in your database/sheet
                    all_transactions.append(modified_transaction)
                
                # Handle removed transactions
                for removed_transaction in response['removed']:
                    # Remove transaction from your database/sheet
                    transaction_id = removed_transaction['transaction_id']
                    # Implement removal logic here
                
                has_more = response['has_more']
                cursor = response['next_cursor']
                
                # Save cursor for this access token
                self.cursors[access_token] = cursor
                self.save_cursors()
                
            except plaid.ApiException as e:
                print(f"Error syncing transactions: {e}")
                if "ITEM_LOGIN_REQUIRED" in str(e):
                    print("User needs to re-authenticate with their bank")
                    # Implement notification system here
                break

        return all_transactions

    def format_transaction(self, transaction: dict) -> list:
        """Format a transaction for Google Sheets"""
        return [
            transaction.get('date', ''),
            transaction.get('name', ''),
            transaction.get('amount', 0.0),
            transaction.get('account_id', ''),
            ', '.join(transaction.get('category', [])),
            transaction.get('personal_finance_category', {}).get('detailed', ''),
            transaction.get('merchant_name', ''),
            transaction.get('transaction_id', '')
        ]