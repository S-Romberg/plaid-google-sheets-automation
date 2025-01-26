from flask import Flask, request
import functions_framework
from google.cloud import secretmanager
import json
import hmac
import hashlib
from plaid_sync import PlaidTransactionSync
from sheets_sync import SheetsSyncer
import os

def get_secret(secret_name):
    """Retrieve secret from Secret Manager"""
    client = secretmanager.SecretManagerServiceClient()
    response = client.access_secret_version(request={"name": f"{secret_name}/versions/latest"})
    return response.payload.data.decode("UTF-8")

# Get secrets
PLAID_CLIENT_ID = get_secret(os.getenv('PLAID_CLIENT_ID_SECRET'))
PLAID_SECRET = get_secret(os.getenv('PLAID_SECRET_SECRET'))
SPREADSHEET_ID = get_secret(os.getenv('SPREADSHEET_ID_SECRET'))
PLAID_TOKENS = json.loads(get_secret(os.getenv('PLAID_TOKENS_SECRET')))

@functions_framework.http
def webhook_handler(request):
    """Handle Plaid webhooks"""
    if request.method != 'POST':
        return 'Only POST requests are accepted', 405

    # Verify webhook signature
    try:
        verify_webhook_signature(request)
    except ValueError as e:
        return str(e), 401

    webhook_data = request.get_json()
    webhook_type = webhook_data.get('webhook_type')
    webhook_code = webhook_data.get('webhook_code')
    item_id = webhook_data.get('item_id')

    # Log webhook for debugging
    print(f"Received webhook: {webhook_type} - {webhook_code}")

    if webhook_type == 'TRANSACTIONS' and webhook_code == 'SYNC_UPDATES_AVAILABLE':
        try:
            # Find access token for this item_id
            access_token = None
            for token, items in PLAID_TOKENS.items():
                if item_id in items:
                    access_token = token
                    break
            
            if not access_token:
                raise ValueError(f"No access token found for item_id: {item_id}")
            
            # Initialize syncers
            syncer = SheetsSyncer()
            
            # Sync transactions
            transactions = syncer.plaid_syncer.sync_transactions(access_token)
            syncer.append_transactions(transactions)
            
            return {
                'success': True,
                'message': f'Processed {len(transactions)} transactions'
            }
        except Exception as e:
            print(f"Error processing webhook: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    return {
        'success': True,
        'message': 'Webhook received but no action needed'
    }

def verify_webhook_signature(request):
    """Verify that the webhook is from Plaid"""
    plaid_signature = request.headers.get('Plaid-Verification')
    if not plaid_signature:
        raise ValueError('No Plaid signature found')

    webhook_secret = get_secret('plaid-webhook-secret')
    body = request.get_data().decode('utf-8')
    
    calculated_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_signature, plaid_signature):
        raise ValueError('Invalid webhook signature')