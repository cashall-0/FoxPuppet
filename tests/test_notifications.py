# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""Tests for the notifications API."""

import pytest
from selenium.common.exceptions import TimeoutException
from typing import Any

from foxpuppet.windows.browser.notifications import BaseNotification
from selenium.webdriver.common.by import By
from foxpuppet.windows.browser.notifications.addons import (
    AddOnInstallBlocked,
    AddOnInstallComplete,
    AddOnInstallConfirmation,
)
from selenium.webdriver.remote.webdriver import WebDriver
from foxpuppet.windows import BrowserWindow
from tests.webserver import WebServer
from selenium.webdriver.firefox.options import Options as FirefoxOptions


@pytest.fixture
def firefox_options(firefox_options: FirefoxOptions) -> FirefoxOptions:
    """Fixture for configuring Firefox."""
    # Due to https://bugzilla.mozilla.org/show_bug.cgi?id=1329939 we need the
    # initial browser window to be in the foreground. Without this, the
    # notifications will not be displayed.
    firefox_options.add_argument("-foreground")
    return firefox_options


class AddOn:
    """Class representing an add-on."""

    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path


@pytest.fixture
def addon() -> AddOn:
    """Fixture for creating an installable add-on.

    Returns:
        :py:class:`AddOn`: Add-on object containing a name and a path to the
            add-on.

    """

    # https://github.com/ambv/black/issues/144#issuecomment-392149599

    return AddOn(name="WebExtension", path="webextension.xpi")


@pytest.fixture
def blocked_notification(
    addon: AddOn, browser: BrowserWindow, webserver: WebServer, selenium: WebDriver
) -> BaseNotification:
    """Fixture causing a blocked notification to appear in Firefox.

    Returns:
        :py:class:`AddOnInstallBlocked`: Firefox notification.

    """
    selenium.get(webserver.url())
    selenium.find_element(By.LINK_TEXT, addon.path).click()
    return browser.wait_for_notification(AddOnInstallBlocked)


@pytest.fixture
def confirmation_notification(
    browser: BrowserWindow, blocked_notification: AddOnInstallBlocked
) -> BaseNotification:
    """Fixture that allows an add-on to be installed.

    Returns:
        :py:class:`AddOnInstallConfirmation`: Firefox notification.

    """
    blocked_notification.allow()
    return browser.wait_for_notification(AddOnInstallConfirmation)


@pytest.fixture
def complete_notification(
    browser: BrowserWindow, confirmation_notification: AddOnInstallConfirmation
) -> BaseNotification:
    """Fixture that installs an add-on.

    Returns:
        :py:class:`AddOnInstallComplete` Firefox notification.

    """
    confirmation_notification.install()
    return browser.wait_for_notification(AddOnInstallComplete)


def test_open_close_notification(
    browser: BrowserWindow, blocked_notification: AddOnInstallBlocked
) -> BaseNotification | None:
    """Trigger and dismiss a notification."""
    assert blocked_notification is not None
    blocked_notification.close()
    return browser.wait_for_notification(None)


@pytest.mark.parametrize(
    "_class, message",
    [
        (BaseNotification, "No notification was shown"),
        (AddOnInstallBlocked, "AddOnInstallBlocked was not shown"),
    ],
)
def test_wait_for_notification_timeout(
    browser: BrowserWindow, _class: Any, message: str
) -> None:
    """Wait for a notification when one is not shown."""
    with pytest.raises(TimeoutException) as excinfo:
        browser.wait_for_notification(_class)
    assert message in str(excinfo.value)


def test_wait_for_no_notification_timeout(
    browser: BrowserWindow, blocked_notification: AddOnInstallBlocked
) -> None:
    """Wait for no notification when one is shown."""
    with pytest.raises(TimeoutException) as excinfo:
        browser.wait_for_notification(None)
    assert "Unexpected notification shown" in str(excinfo.value)


def test_notification_with_origin(
    browser: BrowserWindow,
    webserver: WebServer,
    blocked_notification: AddOnInstallBlocked,
) -> None:
    """Trigger a notification with an origin."""
    assert blocked_notification.origin is not None
    assert f"{webserver.host}" in blocked_notification.origin
    assert blocked_notification.label is not None


def test_allow_blocked_addon(
    browser: BrowserWindow, blocked_notification: AddOnInstallBlocked
) -> None:
    """Allow a blocked add-on installation."""
    blocked_notification.allow()
    browser.wait_for_notification(AddOnInstallConfirmation)


def test_cancel_addon_install(
    browser: BrowserWindow, confirmation_notification: AddOnInstallConfirmation
) -> None:
    """Cancel add-on installation."""
    confirmation_notification.cancel()
    browser.wait_for_notification(None)


def test_confirm_addon_install(
    addon: AddOn,
    browser: BrowserWindow,
    confirmation_notification: AddOnInstallConfirmation,
) -> None:
    """Confirm add-on installation."""
    assert confirmation_notification.addon_name == addon.name
    confirmation_notification.install()
    browser.wait_for_notification(AddOnInstallComplete)


def test_addon_install_complete(
    addon: AddOn, browser: BrowserWindow, complete_notification: AddOnInstallComplete
) -> None:
    """Complete add-on installation and close notification."""
    complete_notification.close()
    browser.wait_for_notification(None)
