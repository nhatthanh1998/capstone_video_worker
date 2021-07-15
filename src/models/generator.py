from torch import nn as nn

class ResnetBlock(nn.Module):
    def __init__(self, dim, padding_type, norm_layer, use_dropout, use_bias):
        super(ResnetBlock, self).__init__()
        self.conv_block = self.build_conv_block(dim, padding_type, norm_layer, use_dropout, use_bias)

    def build_conv_block(self, dim, padding_type, norm_layer, use_dropout, use_bias):
        conv_block = []
        if padding_type == 'reflect':
            conv_block += [nn.ReflectionPad2d(1)]
        else:
            conv_block += [nn.ReplicationPad2d(1)]

        conv_block += [nn.Conv2d(dim, dim, kernel_size=3, bias=use_bias), nn.InstanceNorm2d(dim), nn.ReLU(True)]
        
        if use_dropout:
            conv_block += [nn.Dropout(0.5)]
            
        if padding_type == 'reflect':
            conv_block += [nn.ReflectionPad2d(1)]
        else:
            conv_block += [nn.ReplicationPad2d(1)]
            
        conv_block += [nn.Conv2d(dim, dim, kernel_size=3, bias=use_bias), nn.InstanceNorm2d(dim)]
        return nn.Sequential(*conv_block)

    def forward(self, x):
        out = x + self.conv_block(x)
        return out

class Generator(nn.Module):
    def __init__(self, use_dropout=False, num_residual_block=6):
        super(Generator, self).__init__()
        model = [
            nn.ReflectionPad2d(3),
            nn.Conv2d(3, 32, kernel_size=7, padding=0, stride=1, bias=True),
            nn.InstanceNorm2d(32),
            nn.ReLU(True),
            nn.Conv2d(32, 64, kernel_size=4, padding=1, stride=2, bias=True),
            nn.InstanceNorm2d(64),
            nn.ReLU(True),
            nn.Conv2d(64, 128, kernel_size=4, padding=1, stride=2, bias=True),
            nn.InstanceNorm2d(128),
            nn.ReLU(True),
        ]
        for i in range(num_residual_block):
            model += [ResnetBlock(128, padding_type='reflect', norm_layer=nn.InstanceNorm2d, use_dropout=use_dropout, use_bias=True)]
        
        model += [
            nn.ConvTranspose2d(128, 64, kernel_size=3, stride=2, padding=1, output_padding=1, bias=True),
            nn.InstanceNorm2d(64),
            nn.ReLU(True),
            nn.ConvTranspose2d(64, 32, kernel_size=3, stride=2, padding=1, output_padding=1, bias=True),
            nn.InstanceNorm2d(32),
            nn.ReLU(True),
        ]
        
        model += [nn.ReflectionPad2d(3)]
        model += [nn.Conv2d(32, 3, kernel_size=7, padding=0)]
        model += [nn.Tanh()]
        
        self.model = nn.Sequential(*model)
    def forward(self, x):
        return self.model(x)