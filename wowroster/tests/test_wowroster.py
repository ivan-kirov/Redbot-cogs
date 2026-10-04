import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from wowroster.google_sheet_sync import GoogleSheetSync
from wowroster.roster_ui import RosterUI
import logging

# Disable logging for tests
logging.disable(logging.CRITICAL)

@pytest.mark.asyncio
async def test_google_sheet_auth_success():
    """Test successful Google Sheets authentication."""
    config = {
        'google': {
            'credentials_file': 'test_credentials.json'
        }
    }

    with patch('google.oauth2.service_account.Credentials.from_service_account_file') as mock_from_file:
        mock_creds = MagicMock()
        mock_from_file.return_value = mock_creds
        
        sync = GoogleSheetSync(config)
        await sync.authenticate()
        
        assert sync.creds is not None
        assert sync.sheet_service is not None
        mock_from_file.assert_called_once_with('test_credentials.json',
                                             scopes=['https://www.googleapis.com/auth/spreadsheets'])

@pytest.mark.asyncio
async def test_google_sheet_get_values():
    """Test retrieving values from a Google Sheet."""
    config = {
        'google': {
            'credentials_file': 'test_credentials.json'
        }
    }

    with patch('googleapiclient.discovery.build') as mock_build,
         patch('googleapiclient.errors.HttpError') as mock_error:
        
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_response = {'values': [['Header1', 'Header2'], ['Data1', 'Data2']]}
        mock_service.spreadsheets().values().get().execute.return_value = mock_response
        
        sync = GoogleSheetSync(config)
        await sync.authenticate()
        
        values = await sync.get_sheet_values('test-spreadsheet', 'Sheet1!A1:B2')
        
        assert values == [['Header1', 'Header2'], ['Data1', 'Data2']]
        mock_service.spreadsheets().values().get().execute.assert_called_once_with()

@pytest.mark.asyncio
async def test_google_sheet_update_values():
    """Test updating values in a Google Sheet."""
    config = {
        'google': {
            'credentials_file': 'test_credentials.json'
        }
    }

    with patch('googleapiclient.discovery.build') as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        
        sync = GoogleSheetSync(config)
        await sync.authenticate()
        
        await sync.update_sheet_values('test-spreadsheet', 'Sheet1!A1:B2', [['New1', 'New2']])
        
        mock_service.spreadsheets().values().update().execute.assert_called_once()

@pytest.mark.asyncio
async def test_setup_view_initialization():
    """Test setup view initialization."""
    config = {'user': {}}
    ui = RosterUI(config)
    
    assert ui.config == config

@pytest.mark.asyncio
async def test_spec_selection():
    """Test spec selection handling."""
    config = {'user': {}}
    ui = RosterUI(config)
    
    mock_interaction = AsyncMock()
    mock_interaction.values = ['warrior']
    
    await ui.handle_spec_selection(mock_interaction)
    
    assert ui.config['user']['spec'] == 'warrior'
    mock_interaction.response.send_message.assert_called_once_with(f"Selected spec: warrior", ephemeral=True)

@pytest.mark.asyncio
async def test_confirm_without_spec():
    """Test confirm without selecting a spec."""
    config = {'user': {}}
    ui = RosterUI(config)
    
    mock_interaction = AsyncMock()
    
    await ui.handle_confirm(mock_interaction)
    
    mock_interaction.response.send_message.assert_called_once_with("Please select a spec before confirming.", ephemeral=True)

@pytest.mark.asyncio
async def test_confirm_with_spec():
    """Test confirm with a selected spec."""
    config = {'user': {'spec': 'warrior'}}
    ui = RosterUI(config)
    
    mock_interaction = AsyncMock()
    
    await ui.handle_confirm(mock_interaction)
    
    assert mock_interaction.response.send_message.call_count == 2
    mock_interaction.message.delete.assert_called_once()