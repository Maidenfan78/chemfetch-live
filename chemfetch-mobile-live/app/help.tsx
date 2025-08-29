import React from 'react';
import { ScrollView, View, Text, Linking, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

// ===== Types =====
export type IconName = React.ComponentProps<typeof Ionicons>['name'];

type InfoBoxProps = {
  type?: 'tip' | 'warning' | 'note';
  title: string;
  icon?: IconName;
  children: React.ReactNode;
};

// ===== Minimal, typed InfoBox =====
const InfoBox: React.FC<InfoBoxProps> = ({
  type = 'note',
  title,
  icon = 'information-circle-outline',
  children,
}) => {
  const borderColor = type === 'warning' ? '#F59E0B' : type === 'tip' ? '#10B981' : '#60A5FA';
  const iconName: IconName = icon;

  return (
    <View
      style={{
        borderLeftWidth: 4,
        borderColor,
        padding: 12,
        backgroundColor: '#0B1220',
        borderRadius: 8,
        marginTop: 12,
      }}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 6 }}>
        <Ionicons name={iconName} size={18} />
        <Text style={{ fontWeight: '700', marginLeft: 6 }}>{title}</Text>
      </View>
      <Text>{children}</Text>
    </View>
  );
};

// ===== Minimal Help Screen =====
const HelpScreen: React.FC = () => {
  const openWebHelp = () => {
    // Official online guide: can be updated without a new app release
    void Linking.openURL('https://chemfetch.com/help');
  };

  return (
    <ScrollView contentContainerStyle={{ padding: 16 }}>
      <Text style={{ fontSize: 22, fontWeight: '800', marginBottom: 12 }}>ChemFetch — Help</Text>

      <Text style={{ marginBottom: 12 }}>
        Quick tips for getting started. For the full guide, including screenshots and advanced
        workflows, use the button below.
      </Text>

      <TouchableOpacity
        onPress={openWebHelp}
        style={{
          backgroundColor: '#2563EB',
          paddingVertical: 12,
          paddingHorizontal: 14,
          borderRadius: 10,
          alignSelf: 'flex-start',
          marginBottom: 16,
        }}
        accessibilityRole="button"
        accessibilityLabel="Open the full ChemFetch help site"
      >
        <View style={{ flexDirection: 'row', alignItems: 'center' }}>
          <Ionicons name="open-outline" size={18} />
          <Text style={{ color: 'white', fontWeight: '700', marginLeft: 8 }}>Open Full Guide</Text>
        </View>
      </TouchableOpacity>

      <Text style={{ fontSize: 16, fontWeight: '700', marginTop: 8 }}>Getting started</Text>
      <Text style={{ marginTop: 6 }}>
        1) Sign in • 2) Scan a barcode • 3) Confirm product • 4) View or attach SDS • 5) Save.
      </Text>

      <InfoBox type="tip" title="Better scans" icon="barcode-outline">
        Try steady hands and good lighting. Angle the camera slightly to reduce glare.
      </InfoBox>

      <Text style={{ fontSize: 16, fontWeight: '700', marginTop: 16 }}>Troubleshooting</Text>
      <InfoBox type="warning" title="Scan did not find a match" icon="search-outline">
        Use manual entry and search by product or manufacturer. If still not found, add a note and
        continue; you can link the SDS later.
      </InfoBox>

      <InfoBox type="note" title="SDS did not parse" icon="document-text-outline">
        Some PDFs have unusual layouts. Upload the file and we will extract the key fields on the
        server. Check again after a short while.
      </InfoBox>

      <Text style={{ fontSize: 16, fontWeight: '700', marginTop: 16 }}>Need more detail?</Text>
      <Text>
        Visit the full guide for walkthroughs, screenshots, and admin notes. You can also share the
        page as a PDF for training.
      </Text>
    </ScrollView>
  );
};

export default HelpScreen;
